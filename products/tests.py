from unittest.mock import Mock, patch
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import IntegrityError, connection, transaction
from django.core.management import call_command, CommandError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from products import ai_engine, services
from products.admin import ProductAdmin
from products.forms import ListingWorkflowForm, ProductMessageForm, ProductRequestForm, UserRegistrationForm
from products.models import GeneratedListing, ListingStatus, Product, ProductMessage, ProductRequest, RequestStatus, Review
from products.views import _seller_listing_summary


class BadUrlRedirectTests(SimpleTestCase):
    def test_invalid_quote_path_redirects_to_home(self):
        response = self.client.get('/%E2%80%9D', follow=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


class AiPriceEstimateTests(SimpleTestCase):
    def test_calculate_estimated_price_stays_inside_ebay_market_range(self):
        estimate = ai_engine.calculate_estimated_price(
            original_price=50,
            condition="Like New",
            description="Rare limited edition sneaker in excellent condition with authentic tags.",
            ebay_avg=120,
            ebay_lowest=90,
            ebay_highest=150,
        )

        self.assertGreaterEqual(estimate, 90)
        self.assertLessEqual(estimate, 150)

    def test_run_ai_generation_uses_market_range_for_estimate(self):
        result = ai_engine.run_ai_generation(
            product_name="Nike Dunk Low",
            category="Sneakers",
            condition="Very Good",
            original_price=70,
            ebay_avg=110,
            ebay_lowest=95,
            ebay_highest=130,
            description="Limited edition sneaker in very good condition.",
        )

        self.assertGreaterEqual(result["estimated_resale_price"], 95)
        self.assertLessEqual(result["estimated_resale_price"], 130)


class EbayTokenTests(SimpleTestCase):
    @patch("products.services.requests.post")
    def test_get_access_token_uses_production_endpoint_by_default(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"access_token": "token-123", "expires_in": 7200}
        mock_post.return_value = mock_response

        with patch("products.services.config", return_value="production"), \
             patch("products.services.cache.get", return_value=None), \
             patch("products.services.cache.set") as mock_cache_set, \
             patch.object(settings, "EBAY_CLIENT_ID", "client-id", create=True), \
             patch.object(settings, "EBAY_CLIENT_SECRET", "client-secret", create=True):
            token = services._get_ebay_access_token()

        self.assertEqual(token, "token-123")
        self.assertEqual(mock_post.call_args[0][0], "https://api.ebay.com/identity/v1/oauth2/token")
        mock_cache_set.assert_called_once()


class EbayPriceCurrencyTests(SimpleTestCase):
    @patch("products.services.requests.get")
    @patch("products.services._get_ebay_access_token", return_value="token-123")
    def test_fetch_ebay_prices_uses_only_euro_market_prices(self, mock_token, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "itemSummaries": [
                {"price": {"value": "100.00", "currency": "EUR"}},
                {"price": {"value": "200.00", "currency": "USD"}},
                {"price": {"value": "120.00", "currency": "EUR"}},
            ]
        }
        mock_get.return_value = response

        result = services.fetch_ebay_prices("camera")

        self.assertTrue(result["available"])
        self.assertEqual(result["avg"], 110)
        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(
            mock_get.call_args.kwargs["headers"]["X-EBAY-C-MARKETPLACE-ID"],
            "EBAY_DE",
        )

    @patch("products.services.requests.get")
    @patch("products.services._get_ebay_access_token", return_value="token-123")
    def test_fetch_ebay_prices_rejects_results_without_euros(self, mock_token, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "itemSummaries": [{"price": {"value": "100.00", "currency": "USD"}}]
        }
        mock_get.return_value = response

        result = services.fetch_ebay_prices("camera")

        self.assertFalse(result["available"])
        self.assertIn("EUR", result["error"])


class SecurityBehaviorTests(TestCase):
    def test_logout_requires_post(self):
        self.assertEqual(self.client.get("/logout/").status_code, 405)

    def test_product_request_requires_post(self):
        self.assertEqual(self.client.get("/products/1/request/").status_code, 405)

    def test_ebay_price_refresh_requires_post(self):
        self.assertEqual(self.client.get("/products/1/ebay-check/").status_code, 405)

    def test_login_rejects_external_next_redirect(self):
        User.objects.create_user(username="reseller", password="safe-password-123")

        response = self.client.post(
            "/login/?next=https://example.org/",
            {
                "username": "reseller",
                "password": "safe-password-123",
                "next": "https://example.org/",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")


class RegistrationPasswordValidationTests(TestCase):
    def test_registration_rejects_short_password(self):
        form = UserRegistrationForm(data={
            "username": "new-reseller",
            "email": "reseller@example.com",
            "password": "short",
            "password2": "short",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class RequestChatAuthorizationTests(TestCase):
    def setUp(self):
        self.requester = User.objects.create_user(username="requester", password="safe-password-123")
        self.product = Product.objects.create(
            name="Camera",
            description="Used camera",
            price=100,
            category="Electronics",
        )
        self.product_request = ProductRequest.objects.create(
            product=self.product,
            requester=self.requester,
            message="Is this still available?",
        )
        self.url = reverse("request_chat", args=[self.product_request.pk])
        self.client.force_login(self.requester)

    def test_requester_can_read_and_send_messages(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.url, {"message": "I can collect it tomorrow."})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ProductMessage.objects.filter(
            request=self.product_request,
            sender=self.requester,
            text="I can collect it tomorrow.",
        ).exists())

    def test_requester_cannot_change_request_status(self):
        self.client.post(self.url, {"status": RequestStatus.CLOSED})

        self.product_request.refresh_from_db()
        self.assertEqual(self.product_request.status, RequestStatus.NEW)

    def test_product_request_rejects_message_longer_than_limit(self):
        other_product = Product.objects.create(
            name="Lens",
            description="Used lens",
            price=50,
            category="Electronics",
        )

        response = self.client.post(
            reverse("create_product_request", args=[other_product.pk]),
            {"message": "x" * 1001},
        )

        self.assertRedirects(response, reverse("product_detail", args=[other_product.pk]))
        self.assertFalse(ProductRequest.objects.filter(product=other_product).exists())

    def test_unrelated_user_cannot_read_request_chat(self):
        other_user = User.objects.create_user(username="other", password="safe-password-123")
        self.client.force_login(other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_staff_can_change_request_status(self):
        staff_user = User.objects.create_user(
            username="staff",
            password="safe-password-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.post(self.url, {"status": RequestStatus.CLOSED})

        self.assertEqual(response.status_code, 200)
        self.product_request.refresh_from_db()
        self.assertEqual(self.product_request.status, RequestStatus.CLOSED)

    def test_chat_rejects_messages_longer_than_limit(self):
        response = self.client.post(self.url, {"message": "x" * 2001})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProductMessage.objects.filter(request=self.product_request).exists())
        self.assertIn("message", response.context["message_form"].errors)

    def test_request_forms_enforce_message_limits(self):
        self.assertFalse(ProductRequestForm(data={"message": "x" * 1001}).is_valid())
        self.assertFalse(ProductMessageForm(data={"message": "x" * 2001}).is_valid())

    def test_database_rejects_duplicate_request_for_same_product_and_user(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductRequest.objects.create(product=self.product, requester=self.requester)


class ListingFinanceTests(TestCase):
    def test_net_profit_includes_shipping_and_platform_fees(self):
        listing = GeneratedListing(
            original_price=100,
            estimated_resale_price=200,
            shipping_cost=8,
            platform_fee_percent=Decimal("12.50"),
            platform_fee_fixed=2,
        )

        self.assertEqual(listing.net_profit, Decimal("65.00"))
        self.assertEqual(listing.platform_fee_estimate, Decimal("27.00"))

    def test_realized_profit_uses_actual_sale_price(self):
        listing = GeneratedListing(
            original_price=100,
            estimated_resale_price=200,
            shipping_cost=8,
            platform_fee_percent=Decimal("12.50"),
            platform_fee_fixed=2,
            actual_sale_price=180,
        )

        self.assertEqual(listing.realized_net_profit, Decimal("47.50"))

    def test_sold_listing_requires_actual_sale_price(self):
        form = ListingWorkflowForm(data={"status": "sold", "actual_sale_price": "", "notes": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("actual_sale_price", form.errors)


class SellerSummaryTests(TestCase):
    def test_summary_aggregates_only_the_selected_users_listings(self):
        seller = User.objects.create_user(username="seller", password="safe-password-123")
        other_seller = User.objects.create_user(username="other", password="safe-password-123")
        own_listing = GeneratedListing.objects.create(
            owner=seller,
            product_name="Camera",
            product_category="Electronics",
            original_price=100,
            estimated_resale_price=200,
            demand_score="Medium",
            ai_title="Camera listing",
            ai_description="Camera description",
            shipping_cost=8,
            platform_fee_percent=Decimal("12.50"),
            platform_fee_fixed=2,
            status=ListingStatus.SOLD,
            actual_sale_price=180,
            actual_shipping_cost=5,
            actual_platform_fee=Decimal("15.50"),
        )
        GeneratedListing.objects.create(
            owner=other_seller,
            product_name="Other camera",
            product_category="Electronics",
            original_price=1,
            estimated_resale_price=10000,
            demand_score="Medium",
            ai_title="Other listing",
            ai_description="Other description",
        )

        summary = _seller_listing_summary(GeneratedListing.objects.filter(owner=seller))

        self.assertEqual(summary["listing_counts"]["sold"], 1)
        self.assertEqual(summary["projected_profit"], Decimal("0.00"))
        self.assertEqual(summary["realized_profit"], Decimal("59.50"))


class ProductDetailReviewAggregationTests(TestCase):
    def test_review_summary_and_distribution_are_correct(self):
        product = Product.objects.create(
            name="Camera",
            description="Used camera",
            price=100,
            category="Electronics",
        )
        Review.objects.create(product=product, username="one", rating=5, comment="Great")
        Review.objects.create(product=product, username="two", rating=5, comment="Great")
        Review.objects.create(product=product, username="three", rating=2, comment="Okay")

        response = self.client.get(reverse("product_detail", args=[product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["review_count"], 3)
        self.assertEqual(response.context["avg_rating"], 4.0)
        self.assertEqual(response.context["distribution"][5], {"count": 2, "pct": 67})
        self.assertEqual(response.context["distribution"][2], {"count": 1, "pct": 33})
        self.assertIsInstance(response.context["product_request_form"], ProductRequestForm)


class ProductListQueryTests(TestCase):
    def test_catalog_uses_one_annotated_review_query_for_multiple_products(self):
        for index in range(4):
            Product.objects.create(
                name=f"Camera {index}",
                description="Used camera",
                price=100,
                category="Electronics",
            )

        with CaptureQueriesContext(connection) as captured_queries:
            response = self.client.get(reverse("product_list"))

        self.assertEqual(response.status_code, 200)
        per_product_review_queries = [
            query["sql"]
            for query in captured_queries
            if 'FROM "products_review" WHERE "products_review"."product_id"' in query["sql"]
        ]
        self.assertEqual(per_product_review_queries, [])


class SeedCommandSafetyTests(TestCase):
    @override_settings(DEBUG=False)
    def test_seed_command_refuses_to_run_when_debug_is_disabled(self):
        with self.assertRaisesMessage(CommandError, "nelze seedovat při DEBUG=False"):
            call_command("seed_data")

        self.assertFalse(Product.objects.exists())
        self.assertFalse(Review.objects.exists())


class ProductAdminQueryTests(TestCase):
    def test_review_count_uses_annotated_value_without_extra_queries(self):
        first = Product.objects.create(
            name="First camera", description="Camera", price=100, category="Electronics"
        )
        second = Product.objects.create(
            name="Second camera", description="Camera", price=120, category="Electronics"
        )
        Review.objects.create(product=first, username="one", rating=5, comment="Great")
        Review.objects.create(product=second, username="two", rating=4, comment="Good")
        Review.objects.create(product=second, username="three", rating=5, comment="Great")
        request = RequestFactory().get("/admin/products/product/")
        request.user = User(is_staff=True, is_active=True)
        product_admin = ProductAdmin(Product, admin.site)

        with self.assertNumQueries(1):
            products = list(product_admin.get_queryset(request))
            review_counts = {
                product.name: product_admin.review_count(product) for product in products
            }

        self.assertEqual(review_counts, {"First camera": 1, "Second camera": 2})


class SellerWorkflowIntegrationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username="workflow-seller", password="safe-password-123")
        self.listing = GeneratedListing.objects.create(
            owner=self.seller,
            product_name="Camera",
            product_category="Electronics",
            original_price=100,
            estimated_resale_price=200,
            demand_score="Medium",
            ai_title="Camera listing",
            ai_description="Camera description",
            shipping_cost=8,
            platform_fee_percent=Decimal("12.50"),
            platform_fee_fixed=2,
        )
        self.client.force_login(self.seller)

    def test_sold_transition_uses_actual_sale_costs(self):
        response = self.client.post(
            reverse("update_ai_listing", args=[self.listing.pk]),
            {
                "status": "sold",
                "actual_sale_price": 180,
                "actual_shipping_cost": 5,
                "actual_platform_fee": "15.50",
                "notes": "Sold after negotiation",
            },
        )

        self.assertRedirects(response, reverse("ai_listing_detail", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.SOLD)
        self.assertEqual(self.listing.realized_net_profit, Decimal("59.50"))
        self.assertIsNotNone(self.listing.sold_at)

    def test_listing_detail_is_private_to_its_owner(self):
        other_seller = User.objects.create_user(username="not-owner", password="safe-password-123")
        self.client.force_login(other_seller)

        response = self.client.get(reverse("ai_listing_detail", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 404)

    def test_dashboard_and_inventory_render_for_owner(self):
        dashboard = self.client.get(reverse("seller_dashboard"))
        inventory = self.client.get(reverse("my_ai_listings"))

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Očekávaný čistý zisk")
        self.assertEqual(inventory.status_code, 200)
        self.assertContains(inventory, self.listing.product_name)

    def test_generator_saves_uploaded_photo_and_cost_inputs(self):
        image_bytes = BytesIO()
        Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
        image_file = SimpleUploadedFile("item.png", image_bytes.getvalue(), content_type="image/png")
        form_data = {
            "product_name": "Canvas trainers",
            "product_category": "Sneakers",
            "condition": "Good",
            "description": "Clean pair, size 40.",
            "original_price": 50,
            "shipping_cost": 4,
            "platform_fee_percent": "10.00",
            "platform_fee_fixed": 1,
            "selling_platform": "vinted",
            "image": image_file,
        }

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root), \
             patch("products.views.fetch_ebay_prices", return_value={"available": False}):
            response = self.client.post(reverse("generate_listing"), form_data)
            listing = GeneratedListing.objects.get(product_name="Canvas trainers")

            self.assertRedirects(response, reverse("ai_listing_detail", args=[listing.pk]))
            self.assertTrue(listing.image.storage.exists(listing.image.name))
            self.assertEqual(listing.shipping_cost, 4)
            self.assertEqual(listing.platform_fee_percent, Decimal("10.00"))

    def test_public_catalog_is_paginated(self):
        for index in range(13):
            Product.objects.create(
                name=f"Product {index}",
                description="Catalog test product",
                price=20,
                category="Electronics",
            )

        response = self.client.get(reverse("product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
        self.assertEqual(len(response.context["products"]), 12)
