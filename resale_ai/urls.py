from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from products.views import page_not_found

admin.site.site_header = "ResaleAI Admin"
admin.site.site_title = "ResaleAI"
admin.site.index_title = "Platform Management"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = page_not_found
