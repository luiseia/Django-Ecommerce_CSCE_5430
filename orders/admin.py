from django.contrib import admin

from .models import Order, OrderItem, ReturnRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "product_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "user__email", "shipping_name")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order__order_number", "user__email")
    readonly_fields = ("created_at", "updated_at")