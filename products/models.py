from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from .ai_engine import calculate_estimated_price
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.TextChoices):
    ELECTRONICS  = "Electronics",     "Elektronika"
    SNEAKERS     = "Sneakers",        "Tenisky"
    FASHION      = "Fashion",         "Móda"
    COLLECTIBLES = "Collectibles",    "Sběratelské předměty"
    GAMING       = "Gaming",          "Hry a herní vybavení"
    HOME         = "Home & Lifestyle", "Domov a životní styl"
    SPORTS       = "Sports",          "Sport"
    WATCHES      = "Watches",         "Hodinky"
    STREETWEAR   = "Streetwear",      "Streetwear"
    VINTAGE      = "Vintage",         "Vintage"


class Condition(models.TextChoices):
    NEW          = "New",           "Nové se štítky"
    LIKE_NEW     = "Like New",      "Jako nové"
    VERY_GOOD    = "Very Good",     "Velmi dobrý"
    GOOD         = "Good",          "Dobrý"
    FAIR         = "Fair",          "Opotřebený"


class DemandScore(models.TextChoices):
    HIGH   = "High",   "Vysoká"
    MEDIUM = "Medium", "Střední"
    LOW    = "Low",    "Nízká"


class PriceVerdict(models.TextChoices):
    GREAT    = "great",   "Výhodná cena"
    FAIR     = "fair",    "Přiměřená cena"
    HIGH     = "high",    "Cena nad odhadem"
    UNKNOWN  = "unknown", "Bez cenových dat"


class ListingStatus(models.TextChoices):
    READY = "ready", "Připraveno"
    LISTED = "listed", "Vystaveno"
    SOLD = "sold", "Prodáno"


class SellingPlatform(models.TextChoices):
    VINTED = "vinted", "Vinted"
    EBAY = "ebay", "eBay"
    OTHER = "other", "Jiná"


class RequestStatus(models.TextChoices):
    NEW        = "new",      "New"
    CONTACTED  = "contacted", "Contacted"
    CLOSED     = "closed",   "Closed"


# ─── Public product (admin only) ─────────────────────────────────────────────

class Product(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    price       = models.IntegerField(validators=[MinValueValidator(0)])
    category    = models.CharField(max_length=100, choices=Category.choices)
    image       = models.URLField(blank=True, null=True, max_length=500)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    estimated_price    = models.IntegerField(blank=True, null=True)
    demand_score       = models.CharField(max_length=10, choices=DemandScore.choices, default=DemandScore.MEDIUM)
    ebay_avg_price     = models.IntegerField(blank=True, null=True)
    ebay_lowest_price  = models.IntegerField(blank=True, null=True)
    ebay_highest_price = models.IntegerField(blank=True, null=True)
    ebay_currency      = models.CharField(max_length=3, blank=True, default="USD")
    ebay_result_count  = models.PositiveIntegerField(default=0)
    ebay_fetched_at    = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.estimated_price in (None, 0):
            self.estimated_price = calculate_estimated_price(
                original_price=self.price,
                condition="Good",
                description=self.description,
                ebay_avg=self.ebay_avg_price,
                ebay_lowest=self.ebay_lowest_price,
                ebay_highest=self.ebay_highest_price,
            )
        self.demand_score = DemandScore.HIGH if self.price < 100 else DemandScore.MEDIUM
        super().save(*args, **kwargs)

    @property
    def ai_listing(self):
        ep = self.estimated_price or self.price + 15
        return (
            f"{self.name} za {ep} €. "
            f"Orientační signál poptávky: {self.get_demand_score_display().lower()}. "
            "Před vystavením ověř stav a porovnej podobné nabídky."
        )

    @property
    def vinted_listing(self):
        return (
            f"✨ {self.name}\n\n{self.description}\n\n"
            f"💶 Cena: {self.price} €\n📦 Kategorie: {self.get_category_display()}\n"
            f"✅ Pečlivě zabalím a odešlu podle domluvy.\n\n"
            f"#prodej #{self.category.lower().replace(' ', '')} #zdrunedruheruky"
        )

    @property
    def ebay_listing(self):
        ep = self.estimated_price or self.price + 15
        return (
            f"{self.name} — {self.get_category_display()} | {self.description}\n\n"
            f"Stav: podle popisu\nCena: {self.price} €\nOrientační odhad: {ep} €\n\n"
            "Před nákupem se můžeš zeptat na další podrobnosti."
        )

    @property
    def avg_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0.0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def demand_color(self):
        return {"High": "success", "Medium": "warning", "Low": "secondary"}.get(self.demand_score, "secondary")

    @property
    def ebay_price_vs_asking(self):
        if self.ebay_currency == "EUR" and self.ebay_avg_price and self.price:
            diff = self.ebay_avg_price - self.price
            return {"diff": diff, "pct": round((diff / self.price) * 100), "above": diff > 0}
        return None

    def __str__(self):
        return self.name


class Review(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    username   = models.CharField(max_length=100)
    rating     = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def stars(self): return range(self.rating)

    @property
    def empty_stars(self): return range(5 - self.rating)

    def __str__(self):
        return f"{self.username} → {self.product.name} ({self.rating}★)"


class ProductRequest(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="requests")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_requests")
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_open(self):
        return self.status != RequestStatus.CLOSED

    def __str__(self):
        return f"{self.requester.username} → {self.product.name}"


class ProductMessage(models.Model):
    request = models.ForeignKey(ProductRequest, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:40]}"


class Trend(models.Model):
    name             = models.CharField(max_length=200)
    category         = models.CharField(max_length=100, choices=Category.choices)
    popularity_score = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    description      = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-popularity_score"]

    @property
    def popularity_label(self):
        if self.popularity_score >= 80: return "🔥 Hot"
        elif self.popularity_score >= 50: return "📈 Rising"
        return "📊 Steady"

    @property
    def bar_color(self):
        if self.popularity_score >= 80: return "danger"
        elif self.popularity_score >= 50: return "warning"
        return "info"

    def __str__(self):
        return f"{self.name} ({self.popularity_score})"


# ─── Private AI Listing Generator (normal users) ─────────────────────────────

class GeneratedListing(models.Model):
    owner                  = models.ForeignKey(User, on_delete=models.CASCADE, related_name="generated_listings")
    product_name           = models.CharField(max_length=200)
    product_category       = models.CharField(max_length=100, choices=Category.choices)
    condition              = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    item_description       = models.TextField(blank=True)
    image_url              = models.URLField(blank=True, null=True, max_length=500)
    image                  = models.ImageField(upload_to="listings/%Y/%m/", blank=True)
    original_price         = models.IntegerField(validators=[MinValueValidator(0)])
    estimated_resale_price = models.IntegerField()
    shipping_cost          = models.PositiveIntegerField(default=0)
    platform_fee_percent   = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    platform_fee_fixed     = models.PositiveIntegerField(default=0)
    selling_platform       = models.CharField(max_length=10, choices=SellingPlatform.choices, default=SellingPlatform.OTHER)
    status                 = models.CharField(max_length=10, choices=ListingStatus.choices, default=ListingStatus.READY)
    actual_sale_price      = models.PositiveIntegerField(blank=True, null=True)
    actual_shipping_cost   = models.PositiveIntegerField(blank=True, null=True)
    actual_platform_fee    = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    listed_at              = models.DateTimeField(blank=True, null=True)
    sold_at                = models.DateTimeField(blank=True, null=True)
    notes                  = models.TextField(blank=True)
    demand_score           = models.CharField(max_length=10, choices=DemandScore.choices)
    ai_title               = models.CharField(max_length=300)
    ai_description         = models.TextField()

    # eBay live market data
    ebay_avg_price     = models.IntegerField(blank=True, null=True)
    ebay_lowest_price  = models.IntegerField(blank=True, null=True)
    ebay_highest_price = models.IntegerField(blank=True, null=True)
    ebay_currency      = models.CharField(max_length=3, blank=True, default="USD")
    ebay_result_count  = models.PositiveIntegerField(default=0)
    ebay_fetched_at    = models.DateTimeField(blank=True, null=True)

    # AI verdict
    price_verdict      = models.CharField(max_length=10, choices=PriceVerdict.choices, default=PriceVerdict.UNKNOWN)
    verdict_message    = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Generated Listing"
        verbose_name_plural = "Generated Listings"

    @property
    def demand_color(self):
        return {"High": "success", "Medium": "warning", "Low": "secondary"}.get(self.demand_score, "secondary")

    @property
    def profit_margin(self):
        return self.net_profit

    def _net_profit_for(self, sale_price):
        if sale_price is None:
            return None
        sale_price = Decimal(sale_price)
        fees = sale_price * self.platform_fee_percent / Decimal("100")
        net_profit = (
            sale_price
            - Decimal(self.original_price)
            - Decimal(self.shipping_cost)
            - fees
            - Decimal(self.platform_fee_fixed)
        )
        return net_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def net_profit(self):
        return self._net_profit_for(self.estimated_resale_price)

    @property
    def realized_net_profit(self):
        if self.actual_sale_price is None:
            return None
        sale_price = Decimal(self.actual_sale_price)
        shipping_cost = Decimal(
            self.actual_shipping_cost if self.actual_shipping_cost is not None else self.shipping_cost
        )
        fees = self.actual_platform_fee
        if fees is None:
            fees = sale_price * self.platform_fee_percent / Decimal("100")
            fees += Decimal(self.platform_fee_fixed)
        net_profit = sale_price - Decimal(self.original_price) - shipping_cost - Decimal(fees)
        return net_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def platform_fee_estimate(self):
        sale_price = Decimal(self.estimated_resale_price)
        fees = sale_price * self.platform_fee_percent / Decimal("100")
        return (fees + Decimal(self.platform_fee_fixed)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def vinted_title(self):
        return f"{self.product_name} | {self.condition}"[:100]

    @property
    def ebay_title(self):
        return f"{self.product_name} - {self.condition}"[:80]

    @property
    def vinted_description(self):
        description = self.item_description.strip() or self.ai_description
        return (
            f"{description}\n\nStav: {self.condition}\n"
            f"Cena: {self.estimated_resale_price} €\n\n"
            f"#resale #{self.product_category.lower().replace(' ', '')} #secondhand"
        )

    @property
    def ebay_description(self):
        description = self.item_description.strip() or self.ai_description
        return (
            f"{self.ebay_title}\n\nCondition: {self.condition}\n"
            f"Category: {self.product_category}\n\n{description}\n\n"
            f"Asking price: {self.estimated_resale_price} EUR"
        )

    @property
    def verdict_color(self):
        return {
            "great":   "success",
            "fair":    "warning",
            "high":    "danger",
            "unknown": "secondary",
        }.get(self.price_verdict, "secondary")

    @property
    def verdict_icon(self):
        return {
            "great":   "bi-check-circle-fill",
            "fair":    "bi-dash-circle-fill",
            "high":    "bi-x-circle-fill",
            "unknown": "bi-question-circle-fill",
        }.get(self.price_verdict, "bi-question-circle-fill")

    def __str__(self):
        return f"{self.owner.username} — {self.product_name}"
