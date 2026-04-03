from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from products.models import Product

from .service import get_cart_recommendations, get_home_recommendations, get_product_recommendations


def _serialize(payload):
    return [
        {
            "id": item["product"].pk,
            "name": item["product"].name,
            "slug": item["product"].slug,
            "price": str(item["product"].effective_price),
            "url": item["product"].get_absolute_url(),
            "reason": item["reason"],
            "score": item["score"],
            "strategy": item["strategy"],
        }
        for item in payload
    ]


@require_GET
def api_home_recommendations(request):
    payload = get_home_recommendations(request.user, limit=8)
    return JsonResponse({"recommendations": _serialize(payload)})


@require_GET
def api_product_recommendations(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    payload = get_product_recommendations(product=product, user=request.user, limit=6)
    return JsonResponse({"recommendations": _serialize(payload)})


@require_GET
def api_cart_recommendations(request):
    payload = get_cart_recommendations(request.user, limit=6)
    return JsonResponse({"recommendations": _serialize(payload)})
