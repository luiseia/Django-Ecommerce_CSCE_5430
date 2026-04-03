from django.contrib.auth import get_user_model
from django.test import TestCase

from bookmarks.models import Bookmark
from products.models import Category, Product
from recommendations.models import ProductViewEvent
from recommendations.service import get_cart_recommendations, get_home_recommendations, get_product_recommendations


class RecommendationServiceTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.merchant = self.user_model.objects.create_user(
            email="merchant@example.com",
            password="StrongPass123!",
            role=self.user_model.Role.MERCHANT,
        )
        self.user = self.user_model.objects.create_user(
            email="shopper@example.com",
            password="StrongPass123!",
            role=self.user_model.Role.SHOPPER,
        )

        self.cat_a = Category.objects.create(name="Sports")
        self.cat_b = Category.objects.create(name="Office")

        self.p1 = Product.objects.create(
            merchant=self.merchant,
            category=self.cat_a,
            name="Running Shoes",
            description="Lightweight running sneakers",
            price=100,
            is_active=True,
        )
        self.p2 = Product.objects.create(
            merchant=self.merchant,
            category=self.cat_a,
            name="Gym Bag",
            description="Sports bag for training",
            price=60,
            is_active=True,
        )
        self.p3 = Product.objects.create(
            merchant=self.merchant,
            category=self.cat_b,
            name="Office Chair",
            description="Ergonomic chair",
            price=140,
            is_active=True,
        )

    def test_home_recommendations_for_anonymous_uses_fallback(self):
        class Anonymous:
            is_authenticated = False

        recs = get_home_recommendations(Anonymous(), limit=2)
        self.assertEqual(len(recs), 2)
        self.assertTrue(all(item["strategy"] == "popular" for item in recs))

    def test_home_recommendations_for_authenticated_user_uses_personalized(self):
        ProductViewEvent.objects.create(user=self.user, product=self.p1, view_count=2)
        Bookmark.objects.create(user=self.user, product=self.p1)

        recs = get_home_recommendations(self.user, limit=3)
        self.assertGreaterEqual(len(recs), 1)

    def test_product_recommendations_exclude_current_product(self):
        recs = get_product_recommendations(self.p1, user=self.user, limit=3)
        self.assertTrue(all(item["product"].pk != self.p1.pk for item in recs))

    def test_cart_recommendations_for_user_without_cart_still_returns_data(self):
        recs = get_cart_recommendations(self.user, limit=2)
        self.assertEqual(len(recs), 2)
