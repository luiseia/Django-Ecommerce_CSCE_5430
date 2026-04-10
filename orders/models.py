import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    # Shipping info (snapshot at order time)
    shipping_name = models.CharField(max_length=300)
    shipping_address = models.TextField()
    shipping_phone = models.CharField(max_length=17, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_number} — {self.user.email}"

    def calculate_totals(self):
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.total = self.subtotal + self.shipping_cost
        self.save(update_fields=["subtotal", "total"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True)

    # Snapshot fields (prices can change after the order)
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"
    @property
    def line_total(self):
        if self.product_price is None:
            return 0
        return self.product_price * self.quantity
class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REFUNDED = "REFUNDED", "Refunded"

    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="return_request",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="return_requests",
    )
    quantity = models.PositiveIntegerField(default=1)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        if self.order_item is not None:
            return f"Return request for {self.order_item.product_name}"
        return f"Return request #{self.pk}"

    @property
    def order(self):
        return self.order_item.order