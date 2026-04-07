"""Root URL configuration for ShopProject."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/recommend/", include("recommendations.urls")),
    path("accounts/", include("accounts.urls")),
    path("products/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("cart/", include("cart.urls")),
    path("bookmarks/", include("bookmarks.urls")),
    path("", RedirectView.as_view(pattern_name="products:home", permanent=False)),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
