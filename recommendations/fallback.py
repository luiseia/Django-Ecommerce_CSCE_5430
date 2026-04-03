from typing import Iterable

from products.models import Product

from .algorithms import score_popular_products


def get_popular_recommendations(limit: int = 8, exclude_ids: Iterable[int] | None = None):
    """Return stable popular-product fallback recommendations."""
    exclude_ids = set(exclude_ids or [])
    candidates = Product.objects.filter(is_active=True).exclude(pk__in=exclude_ids)
    ranked = score_popular_products(candidates)
    return ranked[:limit]
