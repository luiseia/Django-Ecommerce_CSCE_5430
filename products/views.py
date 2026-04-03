from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import merchant_required
from bookmarks.models import Bookmark

from .forms import InventoryUpdateForm, ReviewForm
from .models import Category, Inventory, Product, Review
from orders.models import OrderItem, Order


def home(request):
    featured = Product.objects.filter(is_active=True).select_related("inventory")[:8]
    categories = Category.objects.all()

    # Recommendation failures must not block the page.
    recommended_items = []
    try:
        from recommendations.service import get_home_recommendations

        recommended_items = get_home_recommendations(request.user, limit=8)
    except Exception:
        recommended_items = []

    return render(
        request,
        "products/home.html",
        {
            "featured": featured,
            "categories": categories,
            "recommended_items": recommended_items,
        },
    )


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
    bookmarked_ids = set()
    if request.user.is_authenticated:
        bookmarked_ids = set(
            Bookmark.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    return render(
        request,
        "products/product_list.html",
        {"products": products, "categories": categories, "query": query, "bookmarked_ids": bookmarked_ids},
    )


'''def product_detail(request, slug):
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
    is_bookmarked = False
    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()
        if not user_review:
            review_form = ReviewForm()
        is_bookmarked = Bookmark.objects.filter(
            user=request.user, product=product
        ).exists()

    context = {
        "product": product,
        "reviews": reviews,
        "related": related,
        "review_form": review_form,
        "user_review": user_review,
        "is_bookmarked": is_bookmarked,
    }
    return render(request, "products/product_detail.html", context)
'''
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

    recommended_items = []
    try:
        from recommendations.service import get_product_recommendations, track_product_view

        track_product_view(request.user, product)
        recommended_items = get_product_recommendations(product=product, user=request.user, limit=4)
    except Exception:
        recommended_items = []

    user_review = None
    review_form = None
    review_message = None
    is_bookmarked = False

    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()

        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            product=product,
            order__status=Order.Status.DELIVERED,
        ).exists()

        if not user_review and has_purchased:
            review_form = ReviewForm()
        elif not user_review and not has_purchased:
            review_message = "Only customers who purchased and received this product can leave a review."

        is_bookmarked = Bookmark.objects.filter(
            user=request.user, product=product
        ).exists()

    context = {
        "product": product,
        "reviews": reviews,
        "related": related,
        "recommended_items": recommended_items,
        "review_form": review_form,
        "user_review": user_review,
        "review_message": review_message,
        "is_bookmarked": is_bookmarked,
    }
    return render(request, "products/product_detail.html", context)

@login_required
def submit_review(request, slug):
    """Handle review form submission (POST only)."""
    product = get_object_or_404(Product, slug=slug, is_active=True)

    if request.method != "POST":
        return redirect("products:product_detail", slug=slug)

    # Prevent duplicate reviews
    if Review.objects.filter(product=product, user=request.user).exists():
        messages.warning(request, "You have already reviewed this product.")
        return redirect("products:product_detail", slug=slug)

    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__status=Order.Status.DELIVERED,
    ).exists()

    if not has_purchased:
        messages.error(request, "Only customers who purchased and received this product can leave a review.")
        return redirect("products:product_detail", slug=slug)

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
'''def submit_review(request, slug):
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

    return redirect("products:product_detail", slug=slug)'''


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True).select_related("inventory")
    return render(request, "products/category_detail.html", {"category": category, "products": products})


# ---------------------------------------------------------------------------
# Inventory Management (Merchant only)
# ---------------------------------------------------------------------------
@login_required
@merchant_required
def inventory_list(request):
    """Display all inventory records for the merchant's products."""
    products = (
        request.user.products
        .select_related("inventory")
        .order_by("name")
    )
    # Build inventory data with low-stock flag
    inventory_data = []
    for product in products:
        try:
            inv = product.inventory
        except Inventory.DoesNotExist:
            inv = Inventory.objects.create(product=product, quantity=0)
        inventory_data.append({
            "product": product,
            "inventory": inv,
        })

    low_stock_count = sum(1 for d in inventory_data if d["inventory"].is_low_stock)

    return render(request, "products/inventory_list.html", {
        "inventory_data": inventory_data,
        "low_stock_count": low_stock_count,
    })


@login_required
@merchant_required
def inventory_update(request, pk):
    """Allow merchant to restock a product and update low-stock threshold."""
    inventory = get_object_or_404(
        Inventory.objects.select_related("product"),
        pk=pk,
        product__merchant=request.user,
    )

    if request.method == "POST":
        form = InventoryUpdateForm(request.POST, instance=inventory)
        if form.is_valid():
            restock_amount = form.cleaned_data.get("restock_amount")
            form.save()
            if restock_amount:
                inventory.increase(restock_amount)
                messages.success(
                    request,
                    f"Restocked {inventory.product.name} by {restock_amount} units. "
                    f"New stock: {inventory.quantity}.",
                )
            else:
                messages.success(request, f"Updated settings for {inventory.product.name}.")
            return redirect("products:inventory_list")
    else:
        form = InventoryUpdateForm(instance=inventory)

    return render(request, "products/inventory_update.html", {
        "form": form,
        "inventory": inventory,
    })
