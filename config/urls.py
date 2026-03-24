"""
URL configuration for Delivery App project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from restaurants.views import import_products_view, export_products_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-import/import-products/", import_products_view, name="import_products"),
    path("admin-export/export-products/", export_products_view, name="export_products"),
    # Authentication
    path("api/auth/", include("accounts.urls")),
    path("api/addresses/", include("addresses.urls")),
    # Core APIs
    path("api/restaurants/", include("restaurants.urls")),
    path("api/menu/", include("menu.urls")),
    path("api/coupons/", include("coupons.urls")),
    path("api/cart/", include("cart.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/home/", include("home.urls")),
    # Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
