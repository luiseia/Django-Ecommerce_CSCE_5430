from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order, OrderItem
from products.models import Product

from .models import Cart, CartItem


def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_detail(request):
    cart = _get_or_create_cart(request.user)
    recommended_items = []
    try:
        from recommendations.service import get_cart_recommendations

        recommended_items = get_cart_recommendations(request.user, limit=4)
    except Exception:
        recommended_items = []

    return render(
        request,
        "cart/cart_detail.html",
        {
            "cart": cart,
            "recommended_items": recommended_items,
        },
    )


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_or_create_cart(request.user)

    # Check stock availability
    if not product.in_stock:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect("products:product_detail", slug=product.slug)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        new_qty = item.quantity + 1
        if new_qty > product.stock_quantity:
            messages.warning(
                request,
                f"Cannot add more — only {product.stock_quantity} unit(s) of {product.name} available.",
            )
            return redirect("cart:cart_detail")
        item.quantity = new_qty
        item.save()

    messages.success(request, f"Added {product.name} to your cart.")
    return redirect("cart:cart_detail")


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect("cart:cart_detail")


@login_required
def checkout(request):
    cart = _get_or_create_cart(request.user)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    if request.method == "POST":
        # Validate stock for all items before creating the order
        stock_errors = []
        for cart_item in cart.items.select_related("product__inventory"):
            available = cart_item.product.stock_quantity
            if cart_item.quantity > available:
                if available == 0:
                    stock_errors.append(f"{cart_item.product.name} is out of stock.")
                else:
                    stock_errors.append(
                        f"{cart_item.product.name}: only {available} available (you requested {cart_item.quantity})."
                    )

        if stock_errors:
            for err in stock_errors:
                messages.error(request, err)
            return redirect("cart:cart_detail")

        order = Order.objects.create(
            user=request.user,
            shipping_name=request.POST.get("shipping_name", request.user.full_name),
            shipping_address=request.POST.get("shipping_address", ""),
            shipping_phone=request.POST.get("shipping_phone", request.user.phone_number),
        )

        for cart_item in cart.items.select_related("product"):
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.effective_price,
                quantity=cart_item.quantity,
            )
            # Decrease stock via Inventory model
            try:
                cart_item.product.inventory.decrease(cart_item.quantity)
            except (ValueError, cart_item.product.inventory.DoesNotExist.__class__):
                pass

        order.calculate_totals()
        cart.items.all().delete()

        messages.success(request, f"Order {order.order_number} placed successfully!")
        return redirect("orders:order_detail", order_number=order.order_number)

    return render(request, "cart/checkout.html", {"cart": cart})
