from django.contrib import admin

from .models import ProductViewEvent


@admin.register(ProductViewEvent)
class ProductViewEventAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "view_count", "last_viewed_at")
    list_filter = ("last_viewed_at",)
    search_fields = ("user__email", "product__name")
    readonly_fields = ("last_viewed_at",)
