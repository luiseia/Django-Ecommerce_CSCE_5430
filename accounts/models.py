"""
Custom User model for ShopProject.

Key design decisions
--------------------
* **Email as the login identifier** — ``USERNAME_FIELD = "email"`` so users
  authenticate with their email address instead of a separate username.
* **Role field** — a single ``role`` choice field with three values:
  ``SHOPPER``, ``MERCHANT``, and ``ADMINISTRATOR``.  Helper boolean
  properties (``is_shopper``, ``is_merchant``, ``is_administrator``) make
  permission checks clean in views and templates.
* **Profile fields on the User model** — ``first_name``, ``last_name``,
  ``phone_number``, and ``date_of_birth`` live directly on the user to keep
  the schema simple.  A separate ``Profile`` model is not needed unless the
  project grows significantly.
* **Order history** is accessed through the reverse relation from the
  ``Order`` model (``user.orders.all()``).
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    """Custom manager that uses *email* as the unique identifier."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.SHOPPER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMINISTRATOR)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Proxy managers (optional convenience querysets)
# ---------------------------------------------------------------------------
class ShopperManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.SHOPPER)


class MerchantManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.MERCHANT)


class AdministratorManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.ADMINISTRATOR)


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model — email is the login credential, with role-based access.
    """

    class Role(models.TextChoices):
        SHOPPER = "SHOPPER", "Shopper"
        MERCHANT = "MERCHANT", "Merchant"
        ADMINISTRATOR = "ADMIN", "Administrator"

    # --- Authentication fields ---
    email = models.EmailField(
        "email address",
        unique=True,
        db_index=True,
        error_messages={"unique": "A user with that email already exists."},
    )

    # --- Role ---
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.SHOPPER,
    )

    # --- Personal profile fields ---
    first_name = models.CharField("first name", max_length=150, blank=True)
    last_name = models.CharField("last name", max_length=150, blank=True)

    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be in the format: '+999999999'. Up to 15 digits allowed.",
    )
    phone_number = models.CharField(
        "phone number",
        validators=[phone_regex],
        max_length=17,
        blank=True,
    )
    date_of_birth = models.DateField("date of birth", null=True, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    # --- Merchant-specific (optional) ---
    store_name = models.CharField(
        "store / business name",
        max_length=255,
        blank=True,
        help_text="Only relevant for Merchant accounts.",
    )

    # --- Django bookkeeping ---
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField("date joined", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email & password are prompted automatically

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    # --- Convenience properties ---
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_shopper(self):
        return self.role == self.Role.SHOPPER

    @property
    def is_merchant(self):
        return self.role == self.Role.MERCHANT

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR

    def get_order_history(self):
        """Return all orders placed by this user, most recent first."""
        return self.orders.all().order_by("-created_at")


# ---------------------------------------------------------------------------
# Proxy models (optional — useful for role-specific admin views)
# ---------------------------------------------------------------------------
class Shopper(User):
    objects = ShopperManager()

    class Meta:
        proxy = True
        verbose_name = "shopper"
        verbose_name_plural = "shoppers"

    def save(self, *args, **kwargs):
        self.role = User.Role.SHOPPER
        super().save(*args, **kwargs)


class Merchant(User):
    objects = MerchantManager()

    class Meta:
        proxy = True
        verbose_name = "merchant"
        verbose_name_plural = "merchants"

    def save(self, *args, **kwargs):
        self.role = User.Role.MERCHANT
        super().save(*args, **kwargs)


class Administrator(User):
    objects = AdministratorManager()

    class Meta:
        proxy = True
        verbose_name = "administrator"
        verbose_name_plural = "administrators"

    def save(self, *args, **kwargs):
        self.role = User.Role.ADMINISTRATOR
        super().save(*args, **kwargs)
