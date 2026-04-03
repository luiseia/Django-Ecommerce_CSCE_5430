from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg, Sum
from django.utils import timezone

from bookmarks.models import Bookmark
from cart.models import CartItem
from orders.models import OrderItem
from products.models import Product

from .models import ProductViewEvent

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


@dataclass
class ScoredProduct:
    product: Product
    score: float
    reason: str


def _safe_decimal_to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _extract_brand(product: Product) -> str:
    # Compatible with projects that may or may not have a brand field.
    brand = getattr(product, "brand", None)
    if brand is None:
        return ""
    if hasattr(brand, "name"):
        return str(brand.name).strip().lower()
    return str(brand).strip().lower()


def _extract_tags(product: Product) -> set[str]:
    # Compatible with M2M tags, text tags, or no tags at all.
    if not hasattr(product, "tags"):
        return set()

    tags_attr = getattr(product, "tags")
    if hasattr(tags_attr, "all"):
        return {str(tag).strip().lower() for tag in tags_attr.all()}

    if isinstance(tags_attr, str):
        parts = [chunk.strip().lower() for chunk in tags_attr.split(",") if chunk.strip()]
        return set(parts)

    return set()


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {tok.lower() for tok in TOKEN_RE.findall(text) if len(tok) > 2}


def _price_similarity(current_price: float, candidate_price: float) -> float:
    max_price = max(current_price, candidate_price, 1.0)
    diff_ratio = abs(current_price - candidate_price) / max_price
    return max(0.0, 1.0 - diff_ratio)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def score_popular_products(candidates) -> list[ScoredProduct]:
    # Popularity blends sales, rating, and recency with transparent weights.
    now = timezone.now()
    products = list(
        candidates.annotate(
            sold_qty=Sum("orderitem__quantity"),
            avg_rating=Avg("reviews__rating"),
        )
    )

    max_sales = max((p.sold_qty or 0) for p in products) if products else 0

    ranked: list[ScoredProduct] = []
    for product in products:
        sales_score = (product.sold_qty or 0) / max(max_sales, 1)
        rating_score = (product.avg_rating or 0.0) / 5.0

        age_days = max((now - product.created_at).days, 0)
        recency_score = math.exp(-age_days / 45)

        score = sales_score * 0.5 + rating_score * 0.3 + recency_score * 0.2
        ranked.append(
            ScoredProduct(
                product=product,
                score=score,
                reason="Trending recommendation (sales, rating, and recency)",
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def score_similar_products(current_product: Product, candidates) -> list[ScoredProduct]:
    current_category = getattr(current_product, "category_id", None)
    current_brand = _extract_brand(current_product)
    current_tags = _extract_tags(current_product)
    current_desc = _tokenize(current_product.description)
    current_price = _safe_decimal_to_float(current_product.effective_price)

    ranked: list[ScoredProduct] = []

    for product in candidates:
        category_match = 1.0 if current_category and product.category_id == current_category else 0.0

        candidate_brand = _extract_brand(product)
        brand_match = 1.0 if current_brand and candidate_brand and current_brand == candidate_brand else 0.0

        candidate_tags = _extract_tags(product)
        tag_similarity = _jaccard(current_tags, candidate_tags)

        candidate_desc = _tokenize(product.description)
        desc_similarity = _jaccard(current_desc, candidate_desc)

        price_similarity = _price_similarity(
            current_price,
            _safe_decimal_to_float(product.effective_price),
        )

        # If brand/tags are unavailable, description fills part of the signal.
        score = (
            category_match * 0.4
            + brand_match * 0.2
            + tag_similarity * 0.2
            + price_similarity * 0.1
            + desc_similarity * 0.1
        )

        if category_match:
            reason = "Same category as the current product"
        elif brand_match:
            reason = "Similar brand to the current product"
        elif tag_similarity > 0:
            reason = "Similar tags to the current product"
        else:
            reason = "Similar attributes to the current product"

        ranked.append(ScoredProduct(product=product, score=score, reason=reason))

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def build_user_preference_profile(user) -> dict[str, Counter]:
    category_pref: Counter = Counter()
    brand_pref: Counter = Counter()
    tag_pref: Counter = Counter()

    weight = {
        "view": 1,
        "favorite": 3,
        "cart": 4,
        "purchase": 5,
    }

    view_events = ProductViewEvent.objects.filter(user=user).select_related("product__category")
    for event in view_events:
        points = weight["view"] * event.view_count
        product = event.product
        if product.category_id:
            category_pref[product.category_id] += points
        brand = _extract_brand(product)
        if brand:
            brand_pref[brand] += points
        for tag in _extract_tags(product):
            tag_pref[tag] += points

    bookmarks = Bookmark.objects.filter(user=user).select_related("product__category")
    for bookmark in bookmarks:
        points = weight["favorite"]
        product = bookmark.product
        if product.category_id:
            category_pref[product.category_id] += points
        brand = _extract_brand(product)
        if brand:
            brand_pref[brand] += points
        for tag in _extract_tags(product):
            tag_pref[tag] += points

    cart_items = CartItem.objects.filter(cart__user=user).select_related("product__category")
    for item in cart_items:
        points = weight["cart"] * item.quantity
        product = item.product
        if product.category_id:
            category_pref[product.category_id] += points
        brand = _extract_brand(product)
        if brand:
            brand_pref[brand] += points
        for tag in _extract_tags(product):
            tag_pref[tag] += points

    purchases = OrderItem.objects.filter(order__user=user, product__isnull=False).select_related("product__category")
    for item in purchases:
        points = weight["purchase"] * item.quantity
        product = item.product
        if product and product.category_id:
            category_pref[product.category_id] += points
            brand = _extract_brand(product)
            if brand:
                brand_pref[brand] += points
            for tag in _extract_tags(product):
                tag_pref[tag] += points

    return {
        "category": category_pref,
        "brand": brand_pref,
        "tag": tag_pref,
    }


def score_for_user_profile(user, candidates) -> list[ScoredProduct]:
    profile = build_user_preference_profile(user)

    cat_total = sum(profile["category"].values())
    brand_total = sum(profile["brand"].values())
    tag_total = sum(profile["tag"].values())

    if cat_total + brand_total + tag_total == 0:
        return []

    ranked: list[ScoredProduct] = []
    for product in candidates:
        cat_score = 0.0
        if product.category_id and cat_total > 0:
            cat_score = profile["category"][product.category_id] / cat_total

        brand_value = _extract_brand(product)
        brand_score = profile["brand"][brand_value] / brand_total if brand_value and brand_total > 0 else 0.0

        product_tags = _extract_tags(product)
        tag_score = 0.0
        if product_tags and tag_total > 0:
            tag_score = sum(profile["tag"][tag] for tag in product_tags) / tag_total

        score = cat_score * 0.5 + tag_score * 0.3 + brand_score * 0.2
        ranked.append(
            ScoredProduct(
                product=product,
                score=score,
                reason="Based on your recent views, bookmarks, cart, and purchases",
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked
