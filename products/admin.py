from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Product, Review, Trend, ProductRequest, ProductMessage, ListingReport


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "price_display", "estimated_price_display",
        "demand_badge", "review_count", "created_at",
    )
    list_filter = ("category", "demand_score", "created_at")
    search_fields = ("name", "description", "category")
    readonly_fields = ("estimated_price", "demand_score", "created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 25

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_review_count=Count("reviews"))

    fieldsets = (
        ("Product Info", {
            "fields": ("name", "description", "category", "price", "image"),
        }),
        ("AI Analysis (auto-generated)", {
            "fields": ("estimated_price", "demand_score"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def price_display(self, obj):
        return format_html("<strong>{}€</strong>", obj.price)
    price_display.short_description = "Price"

    def estimated_price_display(self, obj):
        return format_html("<span style='color:#10b981;'>{}€</span>", obj.estimated_price or "—")
    estimated_price_display.short_description = "Est. Price"

    def demand_badge(self, obj):
        colors = {"High": "#10b981", "Medium": "#f59e0b", "Low": "#94a3b8"}
        color = colors.get(obj.demand_score, "#94a3b8")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:9999px;font-size:11px;">{}</span>',
            color, obj.demand_score,
        )
    demand_badge.short_description = "Demand"

    def review_count(self, obj):
        return obj._review_count
    review_count.short_description = "Reviews"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 1
    fields = ("username", "rating", "comment", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("username", "product", "rating_stars", "short_comment", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("username", "comment", "product__name")
    ordering = ("-created_at",)
    list_per_page = 30

    def rating_stars(self, obj):
        return "⭐" * obj.rating
    rating_stars.short_description = "Rating"

    def short_comment(self, obj):
        return obj.comment[:60] + ("…" if len(obj.comment) > 60 else "")
    short_comment.short_description = "Comment"


@admin.register(ProductRequest)
class ProductRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "product", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("requester__username", "product__name", "message")
    ordering = ("-created_at",)


@admin.register(ProductMessage)
class ProductMessageAdmin(admin.ModelAdmin):
    list_display = ("request", "sender", "created_at")
    search_fields = ("text", "sender__username")
    ordering = ("-created_at",)


@admin.register(Trend)
class TrendAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "popularity_score", "popularity_label", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "category")
    ordering = ("-popularity_score",)

    def popularity_label(self, obj):
        return obj.popularity_label
    popularity_label.short_description = "Status"


# ─── Generated Listings (read-only for admin oversight) ──────────────────────
from .models import GeneratedListing

@admin.register(GeneratedListing)
class GeneratedListingAdmin(admin.ModelAdmin):
    list_display  = ("owner", "product_name", "product_category", "demand_score",
                     "original_price", "estimated_resale_price", "created_at")
    list_filter   = ("demand_score", "product_category", "created_at")
    search_fields = ("owner__username", "product_name", "ai_title")
    readonly_fields = ("owner", "product_name", "product_category", "original_price",
                       "estimated_resale_price", "demand_score", "ai_title",
                       "ai_description", "created_at")
    ordering      = ("-created_at",)
    list_per_page = 30

    def has_add_permission(self, request):
        return False  # Admins cannot manually create — only users can via generator


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ("listing", "reporter", "reason", "status", "created_at", "reviewed_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("listing__product_name", "reporter__username", "details")
    readonly_fields = ("listing", "reporter", "reason", "details", "created_at")
    list_editable = ("status",)
    ordering = ("status", "created_at")
    list_per_page = 30

