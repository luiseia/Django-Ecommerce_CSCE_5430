from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReturnRequestForm
from .models import Order, ReturnRequest
from .models import Order


@login_required
def order_history(request):
    orders = request.user.get_order_history()
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})
@login_required
def request_return(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if order.status != Order.Status.DELIVERED:
        messages.error(request, "Only delivered orders can be returned.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if hasattr(order, "return_request"):
        messages.warning(request, "A return request has already been submitted for this order.")
        return redirect("orders:order_detail", order_number=order.order_number)

    if request.method == "POST":
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            return_request = form.save(commit=False)
            return_request.order = order
            return_request.user = request.user
            return_request.save()
            messages.success(request, "Your return request has been submitted.")
            return redirect("orders:order_detail", order_number=order.order_number)
    else:
        form = ReturnRequestForm()

    return render(
        request,
        "orders/request_return.html",
        {
            "order": order,
            "form": form,
        },
    )