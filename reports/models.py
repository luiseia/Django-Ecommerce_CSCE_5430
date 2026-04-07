from django.conf import settings
from django.db import models


class MerchantReport(models.Model):
    class Reason(models.TextChoices):
        SCAM = "SCAM", "Scam or fraud"
        FAKE_PRODUCT = "FAKE_PRODUCT", "Fake or misleading product"
        OFFENSIVE = "OFFENSIVE", "Offensive content"
        NON_DELIVERY = "NON_DELIVERY", "Order not delivered"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        REVIEWED = "REVIEWED", "Reviewed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
    )
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_reports",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="merchant_reports",
    )
    reason = models.CharField(max_length=30, choices=Reason.choices)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report against {self.merchant.email} by {self.reporter.email}"