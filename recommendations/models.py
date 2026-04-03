from django.conf import settings
from django.db import models


class ProductViewEvent(models.Model):
    """Lightweight behavior table used only by recommendations."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="product_view_events",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    view_count = models.PositiveIntegerField(default=1)
    last_viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_viewed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_user_product_view_event",
            )
        ]

    def __str__(self):
        return f"{self.user.email} viewed {self.product.name} ({self.view_count})"
