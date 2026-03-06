from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .models import Bookmark


@login_required
def bookmark_list(request):
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        "product", "product__inventory"
    )
    return render(request, "bookmarks/bookmark_list.html", {"bookmarks": bookmarks})


@login_required
def toggle_bookmark(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user, product=product
    )
    if not created:
        bookmark.delete()
        messages.success(request, f'"{product.name}" removed from bookmarks.')
    else:
        messages.success(request, f'"{product.name}" added to bookmarks.')

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("bookmarks:bookmark_list")
