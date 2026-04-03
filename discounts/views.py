from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from accounts.decorators import merchant_required
from orders.models import Order
from cart.models import Cart, CartItem
from .models import DiscountCode, OrderDiscount
from .forms import ApplyDiscountForm, MerchantDiscountForm


# ============================================================================
# SHOPPER VIEWS - 购物者折扣应用
# ============================================================================

@login_required
@require_POST
def validate_discount(request):
    """
    临时验证折扣码（用于结账页面）
    返回折扣金额，但不创建 OrderDiscount 记录
    """
    form = ApplyDiscountForm(request.POST)
    
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'error': form.errors['code'][0]
        })
    
    code = form.cleaned_data['code']
    subtotal = request.POST.get('subtotal', '0')
    
    try:
        subtotal = Decimal(subtotal)
    except:
        return JsonResponse({'success': False, 'error': 'Invalid subtotal'})
    
    try:
        discount_code = DiscountCode.objects.get(code=code, is_active=True)
    except DiscountCode.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Code not found or inactive'})
    
    # 验证代码有效性
    is_valid, message = discount_code.is_valid()
    if not is_valid:
        return JsonResponse({'success': False, 'error': message})
    
    # 验证最小购买金额
    if subtotal < discount_code.min_purchase_amount:
        return JsonResponse({
            'success': False,
            'error': f'Minimum purchase amount: ${discount_code.min_purchase_amount}'
        })
    
    # 检查购物车中的商品是否符合折扣条件
    try:
        cart = request.user.cart
        cart_items = cart.items.all()
        if not cart_items.exists():
            return JsonResponse({'success': False, 'error': 'Your cart is empty'})
        
        # 如果折扣指定了商品，检查购物车中的商品是否都在允许列表中
        if discount_code.products.exists():
            allowed_product_ids = set(discount_code.products.values_list('id', flat=True))
            cart_product_ids = set(item.product.id for item in cart_items)
            
            # 购物车中有不在允许列表中的商品
            if not cart_product_ids.issubset(allowed_product_ids):
                return JsonResponse({
                    'success': False,
                    'error': 'This discount code is not applicable to all products in your cart'
                })
    except Cart.DoesNotExist:
        # 如果没有购物车，无法验证商品，但可以继续（在 apply_discount 时会再次检查）
        pass
    
    # 计算折扣
    discount_amount, final_amount = discount_code.calculate_discount(subtotal)
    
    return JsonResponse({
        'success': True,
        'code': code,
        'discount_amount': float(discount_amount),
        'discount_percentage': float(discount_code.discount_value) if discount_code.discount_type == 'PERCENTAGE' else 0,
        'message': f'Discount applied! You saved ${discount_amount}'
    })


@login_required
@require_POST
def apply_discount(request, order_id):
    """
    AJAX 端点：应用折扣代码到订单
    返回更新后的订单总额
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    
    form = ApplyDiscountForm(request.POST)
    
    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'error': form.errors['code'][0]
        })
    
    code = form.cleaned_data['code']
    
    try:
        discount_code = DiscountCode.objects.get(code=code, is_active=True)
    except DiscountCode.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Code not found or inactive'})
    
    # 验证代码有效性
    is_valid, message = discount_code.is_valid()
    if not is_valid:
        return JsonResponse({'success': False, 'error': message})
    
    # 验证最小购买金额
    if order.subtotal < discount_code.min_purchase_amount:
        return JsonResponse({
            'success': False,
            'error': f'Minimum purchase amount: ${discount_code.min_purchase_amount}'
        })
    
    # 检查订单中的商品是否都符合折扣条件
    order_items = order.items.all()
    if order_items.exists() and discount_code.products.exists():
        # 如果折扣指定了商品列表，订单中的所有商品必须都在列表中
        allowed_product_ids = set(discount_code.products.values_list('id', flat=True))
        for item in order_items:
            if item.product.id not in allowed_product_ids:
                return JsonResponse({
                    'success': False,
                    'error': f'This discount code is not applicable to "{item.product.name}" in your order'
                })
    
    # 移除旧的折扣（如果存在）
    OrderDiscount.objects.filter(order=order).delete()
    
    # 计算新折扣
    discount_amount, final_amount = discount_code.calculate_discount(order.subtotal)
    
    # 保存折扣记录
    OrderDiscount.objects.create(
        order=order,
        discount_code=discount_code,
        discount_amount=discount_amount
    )
    
    # 更新订单
    order.discount_amount = discount_amount
    order.total = final_amount + order.shipping_cost
    order.save(update_fields=['discount_amount', 'total'])
    
    # 增加使用次数
    discount_code.current_uses += 1
    discount_code.save(update_fields=['current_uses'])
    
    return JsonResponse({
        'success': True,
        'discount_amount': float(discount_amount),
        'new_total': float(order.total),
        'message': f'Discount applied! You saved ${discount_amount}'
    })


@login_required
@require_POST
def remove_discount(request, order_id):
    """移除订单上的折扣"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    
    # 删除折扣记录并减少使用次数
    try:
        order_discount = OrderDiscount.objects.get(order=order)
        discount_code = order_discount.discount_code
        discount_code.current_uses -= 1
        discount_code.save(update_fields=['current_uses'])
        order_discount.delete()
    except OrderDiscount.DoesNotExist:
        pass
    
    # 重置订单折扣
    order.discount_amount = 0
    order.total = order.subtotal + order.shipping_cost
    order.save(update_fields=['discount_amount', 'total'])
    
    return JsonResponse({'success': True, 'new_total': float(order.total)})


# ============================================================================
# MERCHANT VIEWS - 商家折扣管理
# ============================================================================

@login_required
@merchant_required
def merchant_discount_list(request):
    """商家查看自己的所有折扣"""
    discounts = request.user.discount_codes.all().order_by('-created_at')
    
    context = {
        'discounts': discounts,
    }
    return render(request, 'discounts/merchant_discount_list.html', context)


@login_required
@merchant_required
def merchant_discount_create(request):
    """商家创建新折扣"""
    if request.method == 'POST':
        form = MerchantDiscountForm(request.POST, merchant=request.user)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.merchant = request.user
            discount.code = discount.code.upper()
            discount.save()
            form.save_m2m()  # 保存 ManyToMany 关系
            messages.success(request, f'Discount "{discount.code}" created successfully!')
            return redirect('discounts:merchant_discount_list')
    else:
        form = MerchantDiscountForm(merchant=request.user)
    
    context = {
        'form': form,
        'title': 'Create New Discount',
    }
    return render(request, 'discounts/merchant_discount_form.html', context)


@login_required
@merchant_required
def merchant_discount_edit(request, discount_id):
    """商家编辑折扣"""
    discount = get_object_or_404(DiscountCode, id=discount_id, merchant=request.user)
    
    if request.method == 'POST':
        form = MerchantDiscountForm(request.POST, instance=discount, merchant=request.user)
        if form.is_valid():
            discount = form.save(commit=False)
            discount.code = discount.code.upper()
            discount.save()
            form.save_m2m()
            messages.success(request, f'Discount "{discount.code}" updated successfully!')
            return redirect('discounts:merchant_discount_list')
    else:
        form = MerchantDiscountForm(instance=discount, merchant=request.user)
    
    context = {
        'form': form,
        'title': f'Edit Discount: {discount.code}',
        'discount': discount,
    }
    return render(request, 'discounts/merchant_discount_form.html', context)


@login_required
@merchant_required
def merchant_discount_delete(request, discount_id):
    """商家删除折扣"""
    discount = get_object_or_404(DiscountCode, id=discount_id, merchant=request.user)
    
    if request.method == 'POST':
        code = discount.code
        discount.delete()
        messages.success(request, f'Discount "{code}" deleted successfully!')
        return redirect('discounts:merchant_discount_list')
    
    context = {
        'discount': discount,
    }
    return render(request, 'discounts/merchant_discount_confirm_delete.html', context)


@login_required
@merchant_required
def merchant_discount_detail(request, discount_id):
    """商家查看折扣详情和使用统计"""
    discount = get_object_or_404(DiscountCode, id=discount_id, merchant=request.user)
    
    # 获取使用这个折扣的订单
    orders_with_discount = Order.objects.filter(
        discount__discount_code=discount
    ).select_related('user').order_by('-created_at')
    
    context = {
        'discount': discount,
        'orders_with_discount': orders_with_discount,
        'usage_stats': {
            'total_uses': discount.current_uses,
            'remaining_uses': discount.max_uses - discount.current_uses if discount.max_uses else 'Unlimited',
            'usage_rate': f"{(discount.current_uses/discount.max_uses*100):.1f}%" if discount.max_uses else 'N/A',
            'applicable_products': discount.products.count(),
        }
    }
    return render(request, 'discounts/merchant_discount_detail.html', context)
