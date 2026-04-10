from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReturnRequestForm
from .models import Order, OrderItem, ReturnRequest
from products.models import Review

@login_required
def order_history(request):
    orders = request.user.get_order_history()
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    review_map = {}
    for item in order.items.select_related("product"):
        if item.product_id:
            review_map[item.id] = Review.objects.filter(
                product=item.product,
                user=request.user,
            ).first()
        else:
            review_map[item.id] = None

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "review_map": review_map,
        },
    )
@login_required
def request_return(request, order_number, item_id):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_item = get_object_or_404(OrderItem, pk=item_id, order=order)

    if order.status != Order.Status.DELIVERED:
        messages.error(request, "Only delivered orders can be returned.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if hasattr(order_item, "return_request"):
        messages.warning(request, "A return request has already been submitted for this item.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if request.method == "POST":
        form = ReturnRequestForm(request.POST, order_item=order_item)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order_item = order_item
            return_request.user = request.user
            return_request.save()
            messages.success(request, "Your return request has been submitted.")
            return redirect("orders:return_request_list", order_number=order.order_number)
    else:
        form = ReturnRequestForm(order_item=order_item)

    return render(
        request,
        "orders/request_return.html",
        {
            "order": order,
            "order_item": order_item,
            "form": form,
        },
    )


@login_required
def return_request_list(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return_requests = ReturnRequest.objects.filter(
        user=request.user,
        order_item__order=order,
    ).select_related("order_item").order_by("-created_at")

    return render(
        request,
        "orders/return_request_list.html",
        {
            "order": order,
            "return_requests": return_requests,
        },
    )