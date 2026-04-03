from __future__ import annotations

import logging

from django.conf import settings

from cart.models import CartItem
from products.models import Product

from .algorithms import ScoredProduct, score_for_user_profile, score_similar_products
from .fallback import get_popular_recommendations
from .models import ProductViewEvent

logger = logging.getLogger(__name__)


def _feature_enabled() -> bool:
    return getattr(settings, "ENABLE_AI_RECOMMENDATIONS", True)


def track_product_view(user, product: Product) -> None:
    """Record view behavior in a dedicated recommendation-only table."""
    if not _feature_enabled():
        return
    if not user.is_authenticated:
        return

    event, created = ProductViewEvent.objects.get_or_create(user=user, product=product)
    if not created:
        event.view_count += 1
        event.save(update_fields=["view_count", "last_viewed_at"])


def _to_payload(recommendations: list[ScoredProduct], strategy: str):
    return [
        {
            "product": item.product,
            "score": round(item.score, 4),
            "reason": item.reason,
            "strategy": strategy,
        }
        for item in recommendations
    ]


def _fill_with_popular(existing: list[ScoredProduct], limit: int, exclude_ids=None) -> list[ScoredProduct]:
    existing = list(existing)
    exclude_ids = set(exclude_ids or [])
    exclude_ids.update(item.product.pk for item in existing)

    if len(existing) >= limit:
        return existing[:limit]

    needed = limit - len(existing)
    fallback = get_popular_recommendations(limit=needed, exclude_ids=exclude_ids)
    existing.extend(fallback)
    return existing[:limit]


def get_home_recommendations(user, limit: int = 8):
    if not _feature_enabled():
        fallback = get_popular_recommendations(limit=limit)
        return _to_payload(fallback, strategy="popular")

    try:
        if not user.is_authenticated:
            fallback = get_popular_recommendations(limit=limit)
            return _to_payload(fallback, strategy="popular")

        candidates = Product.objects.filter(is_active=True).select_related("category")
        personalized = score_for_user_profile(user, candidates)

        if not personalized:
            fallback = get_popular_recommendations(limit=limit)
            return _to_payload(fallback, strategy="popular")

        full_list = _fill_with_popular(personalized, limit=limit)
        return _to_payload(full_list, strategy="personalized")
    except Exception:
        logger.exception("Home recommendations failed, fallback to popular.")
        fallback = get_popular_recommendations(limit=limit)
        return _to_payload(fallback, strategy="popular")


def get_product_recommendations(product: Product, user=None, limit: int = 4):
    if not _feature_enabled():
        fallback = get_popular_recommendations(limit=limit, exclude_ids=[product.pk])
        return _to_payload(fallback, strategy="popular")

    try:
        candidates = Product.objects.filter(is_active=True).exclude(pk=product.pk).select_related("category")
        similar = score_similar_products(product, candidates)
        if user and user.is_authenticated:
            personalized = score_for_user_profile(user, candidates)
            merged = []
            seen = set()
            for item in similar + personalized:
                if item.product.pk in seen:
                    continue
                seen.add(item.product.pk)
                merged.append(item)
            result = _fill_with_popular(merged, limit=limit, exclude_ids=[product.pk])
            return _to_payload(result, strategy="content+personalized")

        result = _fill_with_popular(similar, limit=limit, exclude_ids=[product.pk])
        return _to_payload(result, strategy="content")
    except Exception:
        logger.exception("Product recommendations failed, fallback to popular.")
        fallback = get_popular_recommendations(limit=limit, exclude_ids=[product.pk])
        return _to_payload(fallback, strategy="popular")


def get_cart_recommendations(user, limit: int = 4):
    if not _feature_enabled():
        fallback = get_popular_recommendations(limit=limit)
        return _to_payload(fallback, strategy="popular")

    try:
        if not user.is_authenticated:
            fallback = get_popular_recommendations(limit=limit)
            return _to_payload(fallback, strategy="popular")

        cart_items = list(
            CartItem.objects.filter(cart__user=user).select_related("product__category")
        )

        if not cart_items:
            return get_home_recommendations(user, limit=limit)

        in_cart_ids = {item.product_id for item in cart_items}
        candidates = Product.objects.filter(is_active=True).exclude(pk__in=in_cart_ids).select_related("category")

        merged_scores = {}
        for item in cart_items:
            similar = score_similar_products(item.product, candidates)
            for scored in similar:
                merged_scores.setdefault(scored.product.pk, {"product": scored.product, "score": 0.0, "reason": scored.reason})
                merged_scores[scored.product.pk]["score"] += scored.score

        personalized = score_for_user_profile(user, candidates)
        for scored in personalized:
            merged_scores.setdefault(
                scored.product.pk,
                {"product": scored.product, "score": 0.0, "reason": "You may also need these items"},
            )
            merged_scores[scored.product.pk]["score"] += scored.score

        ranked = [
            ScoredProduct(product=value["product"], score=value["score"], reason=value["reason"])
            for value in merged_scores.values()
        ]
        ranked.sort(key=lambda item: item.score, reverse=True)

        result = _fill_with_popular(ranked, limit=limit, exclude_ids=in_cart_ids)
        return _to_payload(result, strategy="cart-hybrid")
    except Exception:
        logger.exception("Cart recommendations failed, fallback to popular.")
        fallback = get_popular_recommendations(limit=limit)
        return _to_payload(fallback, strategy="popular")
