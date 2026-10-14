from unittest.mock import Mock, patch
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from products import ai_engine, services
from products.forms import ListingWorkflowForm
from products.models import GeneratedListing, ListingStatus, Product
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


class ListingFinanceTests(SimpleTestCase):
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
