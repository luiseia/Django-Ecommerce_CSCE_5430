from django.contrib import admin

from .models import Category, Inventory, Product, Review


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0
    min_num = 1
    fields = ("quantity", "low_stock_threshold", "last_restocked")
    readonly_fields = ("last_restocked",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "merchant",
        "category",
        "price",
        "get_stock",
        "get_avg_rating",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "category", "merchant")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [InventoryInline]

    @admin.display(description="Stock", ordering="inventory__quantity")
    def get_stock(self, obj):
        return obj.stock_quantity

    @admin.display(description="Avg Rating")
    def get_avg_rating(self, obj):
        avg = obj.average_rating
        return f"{avg}/5" if avg else "—"


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "low_stock_threshold", "is_low_stock", "last_restocked", "updated_at")
    list_filter = ("last_restocked",)
    search_fields = ("product__name",)
    readonly_fields = ("updated_at",)

    @admin.display(description="Low Stock?", boolean=True)
    def is_low_stock(self, obj):
        return obj.is_low_stock


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "short_comment", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__email", "comment")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Comment")
    def short_comment(self, obj):
        return obj.comment[:80] + "…" if len(obj.comment) > 80 else obj.comment
