from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ReviewForm
from .models import Category, Product, Review


def home(request):
    featured = Product.objects.filter(is_active=True).select_related("inventory")[:8]
    categories = Category.objects.all()
    return render(request, "products/home.html", {"featured": featured, "categories": categories})


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("inventory")
    query = request.GET.get("q")
    category_slug = request.GET.get("category")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category_slug:
        products = products.filter(category__slug=category_slug)

    categories = Category.objects.all()
    return render(
        request,
        "products/product_list.html",
        {"products": products, "categories": categories, "query": query},
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("inventory", "merchant", "category"),
        slug=slug,
        is_active=True,
    )
    reviews = product.reviews.select_related("user").all()
    related = (
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)[:4]
    )

    # Check if the current user has already reviewed this product
    user_review = None
    review_form = None
    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()
        if not user_review:
            review_form = ReviewForm()

    context = {
        "product": product,
        "reviews": reviews,
        "related": related,
        "review_form": review_form,
        "user_review": user_review,
    }
    return render(request, "products/product_detail.html", context)


@login_required
def submit_review(request, slug):
    """Handle review form submission (POST only)."""
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Prevent duplicate reviews
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.warning(request, "You have already reviewed this product.")
        return redirect("products:product_detail", slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Your review has been submitted!")
        else:
            messages.error(request, "Please correct the errors below.")

    return redirect("products:product_detail", slug=slug)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True).select_related("inventory")
    return render(request, "products/category_detail.html", {"category": category, "products": products})
