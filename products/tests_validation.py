"""
Validation Tests for CSCE 5430 — ShopProject (Django E-commerce)

These end-to-end tests validate three implemented requirements:

  1. Inventory   — The system shall provide Inventory tracking to monitor
                   stock levels.
  2. Bookmarks   — The system shall allow users to save products to a list
                   of Bookmarks for future viewing.
  3. Personal    — The system shall provide a Personal page for each user
      Page        to view their information.

Each test simulates a realistic user flow through the Django test client
(login, navigation, data mutation, verification).

Run with:
    python manage.py test products.tests_validation
or simply:
    python manage.py test
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import Bookmark
from products.models import Category, Inventory, Product

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------
class ValidationBaseTestCase(TestCase):
    """Common set-up: one merchant, one shopper, one category, one product."""

    @classmethod
    def setUpTestData(cls):
        # Merchant that owns the product
        cls.merchant = User.objects.create_user(
            email="merchant@example.com",
            password="StrongPass123!",
            first_name="Molly",
            last_name="Merchant",
            role=User.Role.MERCHANT,
            store_name="Molly's Widgets",
        )

        # Shopper who browses / bookmarks / has a personal page
        cls.shopper = User.objects.create_user(
            email="shopper@example.com",
            password="StrongPass123!",
            first_name="Sam",
            last_name="Shopper",
            phone_number="+15551234567",
            role=User.Role.SHOPPER,
        )

        cls.category = Category.objects.create(name="Widgets")

        cls.product = Product.objects.create(
            merchant=cls.merchant,
            category=cls.category,
            name="Super Widget",
            description="A high-quality test widget.",
            price=Decimal("19.99"),
            is_active=True,
        )

        cls.inventory = Inventory.objects.create(
            product=cls.product,
            quantity=10,
            low_stock_threshold=3,
        )


# ===========================================================================
# 1. Inventory tracking — stock level monitoring
# ===========================================================================
class InventoryTrackingValidationTests(ValidationBaseTestCase):
    """Requirement: system shall track inventory stock levels."""

    def test_VT01_user_views_product_stock_level(self):
        """VT-01: A user (shopper) can view the product and see its stock."""
        self.client.force_login(self.shopper)

        response = self.client.get(
            reverse("products:product_detail", kwargs={"slug": self.product.slug})
        )

        self.assertEqual(response.status_code, 200)
        # The product object is in the template context with live inventory.
        ctx_product = response.context["product"]
        self.assertEqual(ctx_product.stock_quantity, 10)
        self.assertTrue(ctx_product.in_stock)

    def test_VT02_inventory_decrease_is_tracked(self):
        """VT-02: Stock changes (decrease) are persisted and reflected."""
        # Simulate a sale that consumes 4 units.
        self.inventory.decrease(4)
        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.quantity, 6)
        # The related product mirrors the inventory level.
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 6)
        self.assertTrue(self.product.in_stock)

    def test_VT03_inventory_low_stock_and_restock(self):
        """VT-03: Low-stock flag works and restock (increase) updates level."""
        # Drop to exactly the threshold -> low stock.
        self.inventory.decrease(7)  # 10 -> 3
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 3)
        self.assertTrue(self.inventory.is_low_stock)

        # Merchant restocks +10 -> should no longer be low stock.
        self.inventory.increase(10)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 13)
        self.assertFalse(self.inventory.is_low_stock)
        self.assertIsNotNone(self.inventory.last_restocked)

    def test_VT04_merchant_inventory_dashboard_shows_current_stock(self):
        """VT-04: Merchant's inventory dashboard reflects current stock."""
        self.client.force_login(self.merchant)

        # Simulate stock movement before viewing the dashboard.
        self.inventory.decrease(2)  # 10 -> 8

        response = self.client.get(reverse("products:inventory_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Super Widget")
        # The current quantity (8) must appear in the rendered page.
        self.assertContains(response, "8")


# ===========================================================================
# 2. Bookmarks — save products for future viewing
# ===========================================================================
class BookmarkValidationTests(ValidationBaseTestCase):
    """Requirement: users shall be able to bookmark products."""

    def test_VT05_user_can_bookmark_a_product(self):
        """VT-05: A logged-in user can bookmark a product."""
        self.client.force_login(self.shopper)

        # Toggle (add) the bookmark.
        response = self.client.get(
            reverse("bookmarks:toggle_bookmark", kwargs={"product_id": self.product.pk})
        )

        # The view redirects (to bookmark list or referer) on success.
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Bookmark.objects.filter(user=self.shopper, product=self.product).exists(),
            "Bookmark should be created in the database.",
        )

    def test_VT06_user_can_view_bookmark_list_with_product(self):
        """VT-06: The user sees their bookmarked product on the list page."""
        self.client.force_login(self.shopper)
        Bookmark.objects.create(user=self.shopper, product=self.product)

        response = self.client.get(reverse("bookmarks:bookmark_list"))

        self.assertEqual(response.status_code, 200)
        # The product's name is rendered in the bookmark_list template.
        self.assertContains(response, "Super Widget")
        # The context also exposes the bookmark queryset.
        bookmarks = list(response.context["bookmarks"])
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0].product.pk, self.product.pk)

    def test_VT07_toggle_twice_removes_the_bookmark(self):
        """VT-07: Toggling an existing bookmark removes it."""
        self.client.force_login(self.shopper)
        Bookmark.objects.create(user=self.shopper, product=self.product)

        self.client.get(
            reverse("bookmarks:toggle_bookmark", kwargs={"product_id": self.product.pk})
        )

        self.assertFalse(
            Bookmark.objects.filter(user=self.shopper, product=self.product).exists(),
            "Toggling an existing bookmark should delete it.",
        )

    def test_VT08_bookmarks_require_login(self):
        """VT-08: Anonymous users cannot access the bookmark list."""
        response = self.client.get(reverse("bookmarks:bookmark_list"))

        # @login_required redirects to the login URL.
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


# ===========================================================================
# 3. Personal Page — per-user information page
# ===========================================================================
class PersonalPageValidationTests(ValidationBaseTestCase):
    """Requirement: each user shall have a personal page showing their info."""

    def test_VT09_logged_in_user_sees_their_info_on_personal_page(self):
        """VT-09: The personal page renders the logged-in user's info."""
        self.client.force_login(self.shopper)

        response = self.client.get(reverse("accounts:personal_page"))

        self.assertEqual(response.status_code, 200)
        # Email, first and last name should be visible on the page.
        self.assertContains(response, "shopper@example.com")
        self.assertContains(response, "Sam")
        self.assertContains(response, "Shopper")
        # Phone number set in the fixture must also appear.
        self.assertContains(response, "+15551234567")

    def test_VT10_personal_page_requires_authentication(self):
        """VT-10: Unauthenticated access redirects to login."""
        response = self.client.get(reverse("accounts:personal_page"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_VT11_user_can_update_personal_page_information(self):
        """VT-11: A user can update their own info via the personal page."""
        self.client.force_login(self.shopper)

        response = self.client.post(
            reverse("accounts:personal_page"),
            data={
                "first_name": "Samantha",
                "last_name": "Shopper",
                "phone_number": "+15557654321",
                "date_of_birth": "",
                "store_name": "",
            },
        )

        # The view redirects back to the personal page on success.
        self.assertEqual(response.status_code, 302)
        self.shopper.refresh_from_db()
        self.assertEqual(self.shopper.first_name, "Samantha")
        self.assertEqual(self.shopper.phone_number, "+15557654321")

    def test_VT12_personal_page_is_isolated_per_user(self):
        """VT-12: A user only sees their own info, not another user's."""
        self.client.force_login(self.merchant)

        response = self.client.get(reverse("accounts:personal_page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "merchant@example.com")
        self.assertNotContains(response, "shopper@example.com")
