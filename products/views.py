from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Cast, Coalesce
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import (
    Product,
    Review,
    Trend,
    Category,
    GeneratedListing,
    ProductRequest,
    ProductMessage,
    RequestStatus,
    ListingStatus,
    FavoriteListing,
    ListingReport,
)
from .forms import (
    ProductForm,
    ProductMessageForm,
    ProductRequestForm,
    GeneratedListingForm,
    ListingWorkflowForm,
    ListingReportForm,
    UserRegistrationForm,
    StyledLoginForm,
)
from .services import save_ebay_prices_to_product, fetch_ebay_prices
from .ai_engine import run_ai_generation


# ── Auth ──────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Vítej v ResaleAI, {user.username}!")
            return redirect("seller_dashboard")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = StyledLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Vítej zpět, {user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("seller_dashboard")
    else:
        form = StyledLoginForm(request)
    return render(request, "registration/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Byl/a jsi odhlášen/a.")
    return redirect("home")


# ── Public pages ──────────────────────────────────────────────────────────────

def home(request):
    featured_products = Product.objects.prefetch_related("reviews").order_by("-created_at")[:6]
    top_trends        = Trend.objects.order_by("-popularity_score")[:3]
    stats = {
        "total_products":   Product.objects.count(),
        "total_reviews":    Review.objects.count(),
        "total_categories": Product.objects.values("category").distinct().count(),
        "high_demand":      Product.objects.filter(demand_score="High").count(),
    }
    user_listing_count = (
        request.user.generated_listings.count() if request.user.is_authenticated else 0
    )
    return render(request, "home.html", {
        "featured_products":  featured_products,
        "top_trends":         top_trends,
        "stats":              stats,
        "user_listing_count": user_listing_count,
    })


def product_list(request):
    qs         = Product.objects.annotate(
        review_total=Count("reviews"),
        average_rating=Avg("reviews__rating"),
    ).order_by("-created_at")
    categories = Category.choices

    selected_category = request.GET.get("category", "").strip()
    search_query      = request.GET.get("search", "").strip()
    sort_by           = request.GET.get("sort", "newest")

    if selected_category:
        qs = qs.filter(category=selected_category)
    if search_query:
        qs = qs.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    qs = qs.order_by({"newest": "-created_at", "price_asc": "price", "price_desc": "-price", "name": "name"}.get(sort_by, "-created_at"))
    total_count = qs.count()
    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))

    return render(request, "products/product_list.html", {
        "products": page_obj.object_list, "page_obj": page_obj, "categories": categories,
        "selected_category": selected_category,
        "search_query": search_query, "sort_by": sort_by,
        "total_count": total_count,
    })


def product_detail(request, pk):
    product     = get_object_or_404(Product.objects.prefetch_related("reviews"), pk=pk)
    reviews     = product.reviews.order_by("-created_at")
    review_counts = {
        item["rating"]: item["total"]
        for item in reviews.order_by().values("rating").annotate(total=Count("pk"))
    }
    review_count = sum(review_counts.values())
    avg_rating = (
        round(sum(rating * count for rating, count in review_counts.items()) / review_count, 1)
        if review_count
        else 0
    )
    avg_stars   = range(round(avg_rating))
    empty_stars = range(5 - round(avg_rating))
    distribution = {}
    for i in range(5, 0, -1):
        count = review_counts.get(i, 0)
        distribution[i] = {
            "count": count,
            "pct": round((count / review_count) * 100) if review_count else 0,
        }
    related = Product.objects.filter(category=product.category).exclude(pk=pk).order_by("-created_at")[:4]
    return render(request, "products/product_detail.html", {
        "product": product, "reviews": reviews,
        "avg_rating": avg_rating, "avg_stars": avg_stars,
        "empty_stars": empty_stars, "review_count": review_count,
        "product_request_form": ProductRequestForm(),
        "distribution": distribution, "related_products": related,
    })


def page_not_found(request, exception):
    malformed_path = request.path or ""
    if "%E2%80%9D" in malformed_path or any(char in malformed_path for char in "“”‘’«»"):
        return redirect("home")
    return render(request, "404.html", status=404)


def trending(request):
    trends = Trend.objects.all().order_by("-popularity_score")
    hot_products = (
        Product.objects.filter(category__in=trends.values_list("category", flat=True).distinct()[:4])
        .order_by("-created_at")[:8]
    )
    return render(request, "products/trending.html", {
        "trends": trends,
        "max_score": trends.first().popularity_score if trends.exists() else 100,
        "hot_products": hot_products,
    })


def marketplace_listings(request):
    listings = GeneratedListing.objects.filter(
        is_public=True,
        status=ListingStatus.LISTED,
    ).select_related("owner")
    search_query = request.GET.get("search", "").strip()
    selected_category = request.GET.get("category", "").strip()
    if search_query:
        listings = listings.filter(
            Q(product_name__icontains=search_query)
            | Q(item_description__icontains=search_query)
        )
    if selected_category in Category.values:
        listings = listings.filter(product_category=selected_category)
    else:
        selected_category = ""

    page_obj = Paginator(listings.order_by("-listed_at", "-created_at"), 12).get_page(
        request.GET.get("page")
    )
    return render(request, "marketplace/listings.html", {
        "listings": page_obj.object_list,
        "page_obj": page_obj,
        "search_query": search_query,
        "selected_category": selected_category,
        "categories": Category.choices,
    })


def public_listing_detail(request, pk):
    listing = get_object_or_404(
        GeneratedListing.objects.select_related("owner"),
        pk=pk,
        is_public=True,
        status=ListingStatus.LISTED,
    )
    is_favorite = (
        FavoriteListing.objects.filter(user=request.user, listing=listing).exists()
        if request.user.is_authenticated
        else False
    )
    return render(request, "marketplace/listing_detail.html", {
        "listing": listing,
        "is_favorite": is_favorite,
        "report_form": ListingReportForm(),
    })


def seller_profile(request, user_id):
    seller = get_object_or_404(User, pk=user_id, is_active=True)
    listings = GeneratedListing.objects.filter(
        owner=seller,
        is_public=True,
        status=ListingStatus.LISTED,
    ).order_by("-listed_at", "-created_at")
    return render(request, "marketplace/seller_profile.html", {
        "seller": seller,
        "listings": listings,
    })


@login_required(login_url="/login/")
@require_POST
def toggle_favorite_listing(request, pk):
    listing = get_object_or_404(
        GeneratedListing,
        pk=pk,
        is_public=True,
        status=ListingStatus.LISTED,
    )
    if listing.owner_id == request.user.pk:
        messages.error(request, "Vlastní nabídku nelze přidat mezi oblíbené.")
        return redirect("public_listing_detail", pk=listing.pk)

    favorite, created = FavoriteListing.objects.get_or_create(
        user=request.user,
        listing=listing,
    )
    if created:
        messages.success(request, "Nabídka byla přidána do oblíbených.")
    else:
        favorite.delete()
        messages.info(request, "Nabídka byla odebrána z oblíbených.")
    return redirect("public_listing_detail", pk=listing.pk)


@login_required(login_url="/login/")
@require_POST
def report_public_listing(request, pk):
    listing = get_object_or_404(
        GeneratedListing,
        pk=pk,
        is_public=True,
        status=ListingStatus.LISTED,
    )
    if listing.owner_id == request.user.pk:
        messages.error(request, "Vlastní nabídku nelze nahlásit.")
        return redirect("public_listing_detail", pk=listing.pk)

    recent_reports = ListingReport.objects.filter(
        reporter=request.user,
        created_at__gte=timezone.now() - timedelta(hours=1),
    ).count()
    if recent_reports >= 5:
        messages.error(request, "Dosáhl/a jsi hodinového limitu nahlášení.")
        return redirect("public_listing_detail", pk=listing.pk)

    form = ListingReportForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Zkontroluj důvod a délku doplňujících informací.")
        return redirect("public_listing_detail", pk=listing.pk)

    _, created = ListingReport.objects.get_or_create(
        reporter=request.user,
        listing=listing,
        defaults={
            "reason": form.cleaned_data["reason"],
            "details": form.cleaned_data["details"],
        },
    )
    if created:
        messages.success(request, "Nahlášení bylo předáno ke kontrole.")
    else:
        messages.info(request, "Tuto nabídku jsi už nahlásil/a.")
    return redirect("public_listing_detail", pk=listing.pk)


@login_required(login_url="/login/")
def favorite_listings(request):
    favorites = FavoriteListing.objects.filter(
        user=request.user,
        listing__is_public=True,
        listing__status=ListingStatus.LISTED,
    ).select_related("listing", "listing__owner")
    page_obj = Paginator(favorites, 12).get_page(request.GET.get("page"))
    return render(request, "marketplace/favorites.html", {
        "favorites": page_obj.object_list,
        "page_obj": page_obj,
    })


# ── Admin only ────────────────────────────────────────────────────────────────

@require_POST
@login_required(login_url="/login/")
def create_product_request(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.user.is_staff:
        messages.warning(request, "Správci nemohou posílat žádosti o vlastní produkty.")
        return redirect("product_detail", pk=pk)

    form = ProductRequestForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Zpráva je příliš dlouhá.")
        return redirect("product_detail", pk=pk)

    message = form.cleaned_data["message"] or f"I’m interested in {product.name}."
    request_obj, created = ProductRequest.objects.get_or_create(
        product=product,
        requester=request.user,
        defaults={"message": message},
    )
    if not created:
        request_obj.message = message or request_obj.message
        request_obj.status = "new"
        request_obj.save(update_fields=["message", "status", "updated_at"])

    ProductMessage.objects.get_or_create(
        request=request_obj,
        sender=request.user,
        text=message,
    )

    messages.success(request, "Žádost o produkt byla odeslána.")
    return redirect("product_detail", pk=pk)


@staff_member_required(login_url="/login/")
def admin_requests(request):
    requests = ProductRequest.objects.select_related("product", "requester").all()
    return render(request, "products/admin_requests.html", {"requests": requests})


@login_required(login_url="/login/")
def request_chat(request, pk):
    request_obj = get_object_or_404(ProductRequest, pk=pk)
    if not (request.user.is_staff or request.user == request_obj.requester):
        raise Http404

    message_form = ProductMessageForm()
    if request.method == "POST":
        if "status" in request.POST:
            if not request.user.is_staff:
                messages.error(request, "Stav žádosti může změnit pouze správce.")
            else:
                status = request.POST.get("status", "")
                if status in RequestStatus.values:
                    request_obj.status = status
                    request_obj.save(update_fields=["status", "updated_at"])
                    messages.success(request, "Stav žádosti byl uložen.")
                else:
                    messages.error(request, "Zvolený stav žádosti není platný.")
        else:
            message_form = ProductMessageForm(request.POST)
            if message_form.is_valid():
                ProductMessage.objects.create(
                    request=request_obj,
                    sender=request.user,
                    text=message_form.cleaned_data["message"],
                )
                if request.user.is_staff:
                    request_obj.status = "contacted"
                request_obj.save(update_fields=["status", "updated_at"])
                messages.success(request, "Zpráva byla odeslána.")

    return render(request, "products/request_chat.html", {
        "request_obj": request_obj,
        "messages": request_obj.messages.all(),
        "message_form": message_form,
        "status_choices": RequestStatus.choices,
    })


@staff_member_required(login_url="/login/")
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Produkt „{product.name}“ byl uložen. Orientační odhad: {product.estimated_price} €.')
            return redirect("product_detail", pk=product.pk)
    else:
        form = ProductForm()
    return render(request, "products/add_product.html", {"form": form})


@require_POST
@staff_member_required(login_url="/login/")
def check_ebay_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    result  = save_ebay_prices_to_product(product)
    return JsonResponse(result)


# ── User: private AI listing generator ───────────────────────────────────────

@login_required(login_url="/login/")
def generate_listing(request):
    if request.method == "POST":
        form = GeneratedListingForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            # 1. Fetch live eBay price first (used in verdict)
            ebay_result = fetch_ebay_prices(cd["product_name"])
            ebay_avg    = ebay_result.get("avg") if ebay_result.get("available") else None
            ebay_lowest = ebay_result.get("lowest") if ebay_result.get("available") else None
            ebay_highest = ebay_result.get("highest") if ebay_result.get("available") else None

            # 2. Run AI generation (includes verdict)
            ai = run_ai_generation(
                product_name   = cd["product_name"],
                category       = cd["product_category"],
                condition      = cd["condition"],
                original_price = cd["original_price"],
                ebay_avg       = ebay_avg,
                ebay_lowest    = ebay_lowest,
                ebay_highest   = ebay_highest,
                description    = cd.get("description", ""),
            )

            # 3. Save private listing
            listing = GeneratedListing.objects.create(
                owner                  = request.user,
                product_name           = cd["product_name"],
                product_category       = cd["product_category"],
                condition              = cd["condition"],
                item_description       = cd.get("description", ""),
                image_url              = cd.get("image_url") or None,
                image                  = cd.get("image"),
                original_price         = cd["original_price"],
                estimated_resale_price = ai["estimated_resale_price"],
                shipping_cost          = cd["shipping_cost"],
                platform_fee_percent   = cd["platform_fee_percent"],
                platform_fee_fixed     = cd["platform_fee_fixed"],
                selling_platform       = cd["selling_platform"],
                demand_score           = ai["demand_score"],
                ai_title               = ai["ai_title"],
                ai_description         = ai["ai_description"],
                price_verdict          = ai["price_verdict"],
                verdict_message        = ai["verdict_message"],
                ebay_avg_price         = ebay_result.get("avg")     if ebay_result.get("available") else None,
                ebay_lowest_price      = ebay_result.get("lowest")  if ebay_result.get("available") else None,
                ebay_highest_price     = ebay_result.get("highest") if ebay_result.get("available") else None,
                ebay_currency          = ebay_result.get("currency", "") if ebay_result.get("available") else "",
                ebay_result_count      = ebay_result.get("total_results", 0) if ebay_result.get("available") else 0,
                ebay_fetched_at        = timezone.now() if ebay_result.get("available") else None,
            )
            if ebay_result.get("available"):
                messages.success(request, "Nabídka je připravená a obsahuje aktuální ceny aktivních eBay nabídek.")
            else:
                messages.info(request, "Nabídka je připravená. Tržní data eBay teď nejsou dostupná.")
            return redirect("ai_listing_detail", pk=listing.pk)
    else:
        form = GeneratedListingForm()

    recent = GeneratedListing.objects.filter(owner=request.user).order_by("-created_at")[:5]
    return render(request, "generator/generate_listing.html", {"form": form, "recent": recent})


@login_required(login_url="/login/")
def my_ai_listings(request):
    all_listings = GeneratedListing.objects.filter(owner=request.user)
    status_filter = request.GET.get("status", "")
    if status_filter in ListingStatus.values:
        filtered_listings = all_listings.filter(status=status_filter)
    else:
        status_filter = ""
        filtered_listings = all_listings

    page_obj = Paginator(filtered_listings.order_by("-created_at"), 12).get_page(request.GET.get("page"))
    summary = _seller_listing_summary(all_listings)
    return render(request, "generator/my_ai_listings.html", {
        "listings": page_obj.object_list,
        "page_obj": page_obj,
        "status_filter": status_filter,
        **summary,
    })


def _seller_listing_summary(listings):
    counts = listings.aggregate(
        total=Count("pk"),
        ready=Count("pk", filter=Q(status=ListingStatus.READY)),
        listed=Count("pk", filter=Q(status=ListingStatus.LISTED)),
        sold=Count("pk", filter=Q(status=ListingStatus.SOLD)),
    )
    money = DecimalField(max_digits=12, decimal_places=2)

    def net_profit_expression(price_field, use_actual_costs=False):
        sale_price = Cast(F(price_field), money)
        if use_actual_costs:
            shipping_cost = Coalesce(
                Cast(F("actual_shipping_cost"), money), Cast(F("shipping_cost"), money)
            )
            percentage_fee = sale_price * Cast(F("platform_fee_percent"), money) / Value(100, output_field=money)
            estimated_fee = percentage_fee + Cast(F("platform_fee_fixed"), money)
            platform_fee = Coalesce(Cast(F("actual_platform_fee"), money), estimated_fee)
        else:
            shipping_cost = Cast(F("shipping_cost"), money)
            percentage_fee = sale_price * Cast(F("platform_fee_percent"), money) / Value(100, output_field=money)
            platform_fee = percentage_fee + Cast(F("platform_fee_fixed"), money)
        costs = Cast(F("original_price"), money) + shipping_cost + platform_fee
        return ExpressionWrapper(sale_price - costs, output_field=money)

    projected = listings.exclude(status=ListingStatus.SOLD).aggregate(
        total=Sum(net_profit_expression("estimated_resale_price"))
    )["total"]
    realized = listings.filter(
        status=ListingStatus.SOLD,
        actual_sale_price__isnull=False,
    ).aggregate(total=Sum(net_profit_expression("actual_sale_price", use_actual_costs=True)))["total"]
    return {
        "listing_counts": counts,
        "projected_profit": projected or Decimal("0.00"),
        "realized_profit": realized or Decimal("0.00"),
    }


@login_required(login_url="/login/")
def seller_dashboard(request):
    listings = GeneratedListing.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "generator/dashboard.html", {
        **_seller_listing_summary(listings),
        "recent_listings": listings[:6],
    })


@login_required(login_url="/login/")
def ai_listing_detail(request, pk):
    listing = get_object_or_404(GeneratedListing, pk=pk, owner=request.user)
    workflow_form = ListingWorkflowForm(instance=listing)
    return render(request, "generator/ai_listing_detail.html", {
        "listing": listing,
        "workflow_form": workflow_form,
    })


@login_required(login_url="/login/")
@require_POST
def update_ai_listing(request, pk):
    listing = get_object_or_404(GeneratedListing, pk=pk, owner=request.user)
    form = ListingWorkflowForm(request.POST, instance=listing)
    if form.is_valid():
        listing = form.save(commit=False)
        if listing.status == ListingStatus.LISTED and listing.listed_at is None:
            listing.listed_at = timezone.now()
        if listing.status == ListingStatus.SOLD and listing.sold_at is None:
            listing.sold_at = timezone.now()
        elif listing.status != ListingStatus.SOLD:
            listing.sold_at = None
        listing.save()
        messages.success(request, "Stav nabídky byl uložen.")
        return redirect("ai_listing_detail", pk=listing.pk)
    return render(request, "generator/ai_listing_detail.html", {
        "listing": listing,
        "workflow_form": form,
    })


@login_required(login_url="/login/")
def delete_ai_listing(request, pk):
    listing = get_object_or_404(GeneratedListing, pk=pk, owner=request.user)
    if request.method == "POST":
        listing.delete()
        messages.success(request, "Nabídka byla smazána.")
        return redirect("my_ai_listings")
    return redirect("ai_listing_detail", pk=pk)
