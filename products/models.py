from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:category_detail", kwargs={"slug": self.slug})


class Product(models.Model):
    merchant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        limit_choices_to={"role": "MERCHANT"},
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def in_stock(self):
        """Check stock via the related Inventory record."""
        try:
            return self.inventory.quantity > 0
        except Inventory.DoesNotExist:
            return False

    @property
    def stock_quantity(self):
        """Return the current stock level from Inventory."""
        try:
            return self.inventory.quantity
        except Inventory.DoesNotExist:
            return 0

    @property
    def average_rating(self):
        """Return the average review rating, or None if no reviews."""
        avg = self.reviews.aggregate(models.Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg is not None else None

    @property
    def review_count(self):
        return self.reviews.count()


# ---------------------------------------------------------------------------
# Inventory — separate model to track stock levels per product
# ---------------------------------------------------------------------------
class Inventory(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.PositiveIntegerField(
        default=0,
        help_text="Number of units currently in stock.",
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Alert when stock falls to or below this level.",
    )
    last_restocked = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "inventory record"
        verbose_name_plural = "inventory"

    def __str__(self):
        return f"{self.product.name} — {self.quantity} in stock"

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def decrease(self, amount=1):
        """Decrease stock by *amount*. Raises ValueError if insufficient."""
        if amount > self.quantity:
            raise ValueError(
                f"Cannot decrease stock by {amount} — only {self.quantity} available."
            )
        self.quantity -= amount
        self.save(update_fields=["quantity", "updated_at"])

    def increase(self, amount=1):
        """Increase stock by *amount* (e.g. after a restock)."""
        from django.utils import timezone

        self.quantity += amount
        self.last_restocked = timezone.now()
        self.save(update_fields=["quantity", "last_restocked", "updated_at"])


# ---------------------------------------------------------------------------
# Review — links a User to a Product with a 1-5 rating and comment
# ---------------------------------------------------------------------------
class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (worst) to 5 (best).",
    )
    comment = models.TextField(
        help_text="Write your review here.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # One review per user per product
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                name="unique_review_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user.email} — {self.product.name} ({self.rating}/5)"
