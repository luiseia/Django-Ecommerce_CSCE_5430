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
    return render(request, "cart/cart_detail.html", {"cart": cart})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = _get_or_create_cart(request.user)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
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
