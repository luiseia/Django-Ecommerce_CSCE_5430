from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product
from .forms import MerchantReportForm
from .models import MerchantReport


@login_required
def report_merchant(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("merchant"),
        slug=slug,
        is_active=True,
    )
    merchant = product.merchant

    if request.method == "POST":
        form = MerchantReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.merchant = merchant
            report.product = product
            report.save()
            messages.success(request, "Your report has been submitted.")
            return redirect("products:product_detail", slug=product.slug)
    else:
        form = MerchantReportForm()

    return render(
        request,
        "reports/report_merchant.html",
        {
            "form": form,
            "product": product,
            "merchant": merchant,
        },
    )