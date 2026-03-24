"""
Menu URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MenuCategoryViewSet,
    ProductViewSet,
    ProductVariationsView,
    ProductAddonsView,
)

router = DefaultRouter()
router.register(r"categories", MenuCategoryViewSet, basename="menu-category")
router.register(r"products", ProductViewSet, basename="product")

urlpatterns = [
    path(
        "products/<int:product_id>/variations/",
        ProductVariationsView.as_view(),
        name="product-variations",
    ),
    path(
        "products/<int:product_id>/addons/",
        ProductAddonsView.as_view(),
        name="product-addons",
    ),
    path("", include(router.urls)),
]
