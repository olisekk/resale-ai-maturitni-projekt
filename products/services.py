"""
products/services.py
eBay market price lookup via official eBay Browse API with OAuth.
"""
import requests
import base64

from decouple import config
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from .ai_engine import calculate_estimated_price


EBAY_TOKEN_CACHE_KEY = "ebay_oauth_token"


def _get_ebay_endpoints() -> tuple[str, str]:
    environment = (
        getattr(settings, "EBAY_ENVIRONMENT", "").strip().lower()
        or config("EBAY_ENVIRONMENT", default="production").strip().lower()
    )

    if environment == "sandbox":
        return (
            "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
            "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search",
        )

    return (
        "https://api.ebay.com/identity/v1/oauth2/token",
        "https://api.ebay.com/buy/browse/v1/item_summary/search",
    )


def _get_ebay_access_token() -> str:
    """
    Get OAuth access token from eBay using client_credentials grant.
    Caches the token to avoid repeated API calls.
    """
    cached_token = cache.get(EBAY_TOKEN_CACHE_KEY)
    if cached_token:
        return cached_token

    client_id = getattr(settings, "EBAY_CLIENT_ID", "").strip() or config("EBAY_CLIENT_ID", default="").strip()
    client_secret = getattr(settings, "EBAY_CLIENT_SECRET", "").strip() or config("EBAY_CLIENT_SECRET", default="").strip()
    token_endpoint, _ = _get_ebay_endpoints()

    if not client_id or not client_secret:
        return ""

    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # ✓ OPRAVENÝ SCOPE — toto je jediná správná hodnota pro client_credentials
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    try:
        resp = requests.post(token_endpoint, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        token_data    = resp.json()
        access_token  = token_data.get("access_token", "")

        if access_token:
            expires_in = token_data.get("expires_in", 7200)
            cache_ttl  = max(expires_in - 60, 60)
            cache.set(EBAY_TOKEN_CACHE_KEY, access_token, cache_ttl)
            return access_token

        return ""

    except requests.exceptions.RequestException:
        return ""


def fetch_ebay_prices(product_name: str) -> dict:
    """
    Search eBay Browse API for a product and return pricing statistics.

    Returns:
        {
            "available": True,
            "avg":     int,
            "lowest":  int,
            "highest": int,
            "currency": "USD",
            "total_results": int,
        }
        or
        {
            "available": False,
            "error": "...",
        }
    """
    access_token = _get_ebay_access_token()
    _, search_endpoint = _get_ebay_endpoints()
    if not access_token:
        return {"available": False, "error": "Failed to obtain eBay access token"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
        "X-EBAY-C-MARKETPLACE-ID": getattr(settings, "EBAY_MARKETPLACE_ID", "EBAY_DE"),
    }

    params = {
        "q":      product_name,
        "limit":  50,
        "filter": "buyingOptions:{FIXED_PRICE}",
    }

    try:
        resp = requests.get(search_endpoint, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data  = resp.json()
        items = data.get("itemSummaries", [])

        if not items:
            return {
                "available":     False,
                "error":         "No items found on eBay for this product",
                "total_results": data.get("total", 0),
            }

        prices = []
        for item in items:
            price_data = item.get("price", {})
            if not isinstance(price_data, dict) or price_data.get("currency") != "EUR":
                continue
            value      = price_data.get("value") if isinstance(price_data, dict) else price_data
            if value:
                try:
                    prices.append(float(value))
                except (ValueError, TypeError):
                    pass

        if not prices:
            return {"available": False, "error": "No EUR-priced eBay items found"}

        return {
            "available":     True,
            "avg":           int(round(sum(prices) / len(prices))),
            "lowest":        int(min(prices)),
            "highest":       int(max(prices)),
            "total_results": len(prices),
            "currency":      "EUR",
        }

    except requests.exceptions.Timeout:
        return {"available": False, "error": "eBay API request timed out"}

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {e.response.status_code}"
        try:
            detail = e.response.json().get("errors", [{}])[0].get("message", "")
            if detail:
                error_msg += f": {detail}"
        except Exception:
            pass
        return {"available": False, "error": error_msg}

    except requests.exceptions.RequestException as e:
        return {"available": False, "error": str(e)}

    except (KeyError, ValueError, TypeError) as e:
        return {"available": False, "error": f"Could not parse response: {e}"}


def save_ebay_prices_to_product(product) -> dict:
    """
    Fetch eBay prices and persist them on the Product instance.
    Returns the result dict from fetch_ebay_prices().
    """
    result = fetch_ebay_prices(product.name)
    if result["available"]:
        product.ebay_avg_price     = result["avg"]
        product.ebay_lowest_price  = result.get("lowest")
        product.ebay_highest_price = result.get("highest")
        product.ebay_currency      = result["currency"]
        product.ebay_result_count  = result["total_results"]
        product.estimated_price    = calculate_estimated_price(
            original_price=product.price,
            condition="Good",
            description=product.description,
            ebay_avg=result.get("avg"),
            ebay_lowest=result.get("lowest"),
            ebay_highest=result.get("highest"),
        )
        product.ebay_fetched_at    = timezone.now()
        product.save(update_fields=[
            "ebay_avg_price", "ebay_lowest_price",
            "ebay_highest_price", "estimated_price", "ebay_fetched_at",
            "ebay_currency",
            "ebay_result_count",
        ])
    return result
