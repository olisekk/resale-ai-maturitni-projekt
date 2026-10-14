from django.urls import path
from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────────────────────
    path("",                              views.home,             name="home"),
    path("products/",                     views.product_list,     name="product_list"),
    path("products/<int:pk>/",            views.product_detail,   name="product_detail"),
    path("trending/",                     views.trending,         name="trending"),

    # ── Admin only ───────────────────────────────────────────────────────────
    path("products/add/",                 views.add_product,      name="add_product"),
    path("products/<int:pk>/ebay-check/", views.check_ebay_price, name="check_ebay_price"),
    path("products/<int:pk>/request/", views.create_product_request, name="create_product_request"),
    path("dashboard/requests/", views.admin_requests, name="admin_requests"),
    path("dashboard/requests/<int:pk>/", views.request_chat, name="request_chat"),

    # ── Auth ─────────────────────────────────────────────────────────────────
    path("login/",                        views.login_view,       name="login"),
    path("logout/",                       views.logout_view,      name="logout"),
    path("register/",                     views.register_view,    name="register"),

    # ── User: private AI generator ───────────────────────────────────────────
    path("generate-listing/",             views.generate_listing,   name="generate_listing"),
    path("dashboard/",                    views.seller_dashboard,   name="seller_dashboard"),
    path("my-ai-listings/",               views.my_ai_listings,     name="my_ai_listings"),
    path("my-ai-listings/<int:pk>/",      views.ai_listing_detail,  name="ai_listing_detail"),
    path("my-ai-listings/<int:pk>/update/", views.update_ai_listing, name="update_ai_listing"),
    path("my-ai-listings/<int:pk>/delete/", views.delete_ai_listing, name="delete_ai_listing"),
]
