def cart_item_count(request):
    """Make cart item count available in every template."""
    if request.user.is_authenticated:
        try:
            count = request.user.cart.item_count
        except Exception:
            count = 0
    else:
        count = 0
    return {"cart_item_count": count}
