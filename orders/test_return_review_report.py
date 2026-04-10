from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from orders.models import Order, OrderItem, ReturnRequest
from products.models import Category, Product, Review
from reports.models import MerchantReport


class BaseValidationTestCase(TestCase):
    """
    Base setup shared by all validation tests.

    Creates:
    - one shopper user
    - one merchant user
    - one category
    - one active product sold by the merchant
    """

    def setUp(self):
        self.shopper = User.objects.create_user(
            email="shopper@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Shopper",
            role=User.Role.SHOPPER,
        )

        self.merchant = User.objects.create_user(
            email="merchant@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Merchant",
            role=User.Role.MERCHANT,
            store_name="Test Store",
        )

        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
        )

        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            description="Validation product",
            price=Decimal("19.99"),
            category=self.category,
            merchant=self.merchant,
            is_active=True,
        )

    def create_order_with_item(self, *, status, quantity=2):
        """
        Helper to create an order and one order item for the shopper.
        """
        order = Order.objects.create(
            user=self.shopper,
            status=status,
            shipping_name="Test Shopper",
            shipping_address="123 Test Street",
            shipping_phone="1234567890",
            subtotal=Decimal("19.99"),
            shipping_cost=Decimal("0.00"),
            total=Decimal("19.99"),
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            quantity=quantity,
        )
        return order, item


class ReviewValidationTests(BaseValidationTestCase):
    # ---------------------------
    # R15: Product rating / review
    # ---------------------------

    def test_review_blocked_without_delivered_purchase(self):
        """
        Validates that a user cannot submit a review
        if they have not purchased and received the product.
        """
        self.client.force_login(self.shopper)

        response = self.client.post(
            reverse("products:submit_review", args=[self.product.slug]),
            {"rating": 5, "comment": "Great product"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 0)

    def test_review_allowed_with_delivered_purchase(self):
        """
        Validates that a user can submit a review
        after purchasing the product in a DELIVERED order.
        """
        self.client.force_login(self.shopper)
        self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.post(
            reverse("products:submit_review", args=[self.product.slug]),
            {"rating": 5, "comment": "Delivered and reviewed"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.get()
        self.assertEqual(review.user, self.shopper)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Delivered and reviewed")

    def test_review_form_visible_on_order_detail_for_delivered_item(self):
        """
        Validates that the order detail page shows the review entry point
        for DELIVERED items.
        """
        self.client.force_login(self.shopper)
        order, _ = self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Write Review")

    def test_review_form_not_visible_on_order_detail_for_pending_item(self):
        """
        Validates that the order detail page does not show
        the review entry point for non-delivered items.
        """
        self.client.force_login(self.shopper)
        order, _ = self.create_order_with_item(status=Order.Status.PENDING)

        response = self.client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Write Review")

    def test_edit_review_page_loads_for_existing_review(self):
        """
        Validates that an existing review can be opened
        from the edit/view review page.
        """
        self.client.force_login(self.shopper)
        self.create_order_with_item(status=Order.Status.DELIVERED)

        Review.objects.create(
            product=self.product,
            user=self.shopper,
            rating=4,
            comment="Original comment",
        )

        response = self.client.get(
            reverse("products:edit_review", args=[self.product.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View / Edit Review")
        self.assertContains(response, "Original comment")

    def test_edit_review_updates_existing_review(self):
        """
        Validates that the user can update an existing review
        instead of creating a duplicate one.
        """
        self.client.force_login(self.shopper)
        self.create_order_with_item(status=Order.Status.DELIVERED)

        Review.objects.create(
            product=self.product,
            user=self.shopper,
            rating=4,
            comment="Original comment",
        )

        response = self.client.post(
            reverse("products:edit_review", args=[self.product.slug]),
            {"rating": 5, "comment": "Updated comment"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Review.objects.count(), 1)

        review = Review.objects.get()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Updated comment")


class MerchantReportValidationTests(BaseValidationTestCase):
    # ---------------------------
    # R16: Report merchant
    # ---------------------------

    def test_report_merchant_button_visible_on_product_page(self):
        """
        Validates that the product detail page shows
        the 'Report Merchant' entry point.
        """
        self.client.force_login(self.shopper)

        response = self.client.get(
            reverse("products:product_detail", args=[self.product.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Merchant")

    def test_report_merchant_page_loads(self):
        """
        Validates that the report merchant form page can be opened.
        """
        self.client.force_login(self.shopper)

        response = self.client.get(
            reverse("reports:report_merchant", args=[self.product.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Merchant")
        self.assertContains(response, "Submit Report")

    def test_report_merchant_submission(self):
        """
        Validates that submitting a merchant report creates a MerchantReport record.
        """
        self.client.force_login(self.shopper)

        response = self.client.post(
            reverse("reports:report_merchant", args=[self.product.slug]),
            {
                "reason": MerchantReport.Reason.OTHER,
                "description": "Testing merchant report submission.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(MerchantReport.objects.count(), 1)

        report = MerchantReport.objects.get()
        self.assertEqual(report.reporter, self.shopper)
        self.assertEqual(report.merchant, self.merchant)
        self.assertEqual(report.product, self.product)
        self.assertEqual(report.status, MerchantReport.Status.PENDING)


class ReturnRequestValidationTests(BaseValidationTestCase):
    # ---------------------------
    # R17: Return request
    # ---------------------------

    def test_request_return_button_visible_for_delivered_item(self):
        """
        Validates that a DELIVERED order item shows
        the 'Request Return' button on the order detail page.
        """
        self.client.force_login(self.shopper)
        order, _ = self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Request Return")

    def test_request_return_button_not_visible_for_pending_item(self):
        """
        Validates that a non-delivered order item does not show
        the 'Request Return' button.
        """
        self.client.force_login(self.shopper)
        order, _ = self.create_order_with_item(status=Order.Status.PENDING)

        response = self.client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Request Return")

    def test_return_request_page_loads_for_delivered_item(self):
        """
        Validates that the return request form page opens
        for a DELIVERED order item.
        """
        self.client.force_login(self.shopper)
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.get(
            reverse("orders:request_return", args=[order.order_number, item.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Request Return")
        self.assertContains(response, "Submit Return Request")

    def test_return_request_blocked_for_pending_order(self):
        """
        Validates that return requests are blocked
        for non-delivered orders.
        """
        self.client.force_login(self.shopper)
        order, item = self.create_order_with_item(status=Order.Status.PENDING)

        response = self.client.post(
            reverse("orders:request_return", args=[order.order_number, item.id]),
            {
                "quantity": 1,
                "reason": "Want to return this item",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReturnRequest.objects.count(), 0)

    def test_return_request_allowed_for_delivered_order_item(self):
        """
        Validates that a DELIVERED order item can create a return request successfully.
        """
        self.client.force_login(self.shopper)
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED, quantity=2)

        response = self.client.post(
            reverse("orders:request_return", args=[order.order_number, item.id]),
            {
                "quantity": 1,
                "reason": "Received wrong item",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReturnRequest.objects.count(), 1)

        req = ReturnRequest.objects.get()
        self.assertEqual(req.user, self.shopper)
        self.assertEqual(req.order_item, item)
        self.assertEqual(req.quantity, 1)
        self.assertEqual(req.status, ReturnRequest.Status.REQUESTED)

    def test_return_request_quantity_cannot_exceed_purchased_quantity(self):
        """
        Validates that the return quantity cannot exceed
        the quantity originally purchased.
        """
        self.client.force_login(self.shopper)
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED, quantity=2)

        response = self.client.post(
            reverse("orders:request_return", args=[order.order_number, item.id]),
            {
                "quantity": 5,
                "reason": "Trying to return too many",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You cannot return more than you purchased.")
        self.assertEqual(ReturnRequest.objects.count(), 0)

    def test_return_request_status_page_loads(self):
        """
        Validates that the return request status/list page can be opened
        and shows the created request.
        """
        self.client.force_login(self.shopper)
        order, item = self.create_order_with_item(status=Order.Status.DELIVERED, quantity=2)

        ReturnRequest.objects.create(
            order_item=item,
            user=self.shopper,
            quantity=1,
            reason="Checking status page",
            status=ReturnRequest.Status.REQUESTED,
        )

        response = self.client.get(
            reverse("orders:return_request_list", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Return Requests")
        self.assertContains(response, item.product_name)
        self.assertContains(response, "Requested")

    def test_view_return_requests_button_visible_on_order_detail(self):
        """
        Validates that the order detail page shows
        the 'View Return Requests' button.
        """
        self.client.force_login(self.shopper)
        order, _ = self.create_order_with_item(status=Order.Status.DELIVERED)

        response = self.client.get(
            reverse("orders:order_detail", args=[order.order_number])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Return Requests")