"""
Restaurant URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RestaurantViewSet,
    RestaurantCategoryViewSet,
    RestaurantSearchView,
    RestaurantChoicesView,
)

router = DefaultRouter()
router.register(
    r"categories", RestaurantCategoryViewSet, basename="restaurant-category"
)
router.register(r"", RestaurantViewSet, basename="restaurant")

urlpatterns = [
    # urls.py
    path(
        "restaurants/choices/",
        RestaurantChoicesView.as_view(),
        name="restaurant-choices",
    ),
    path("search/", RestaurantSearchView.as_view(), name="restaurant-search"),
    path("", include(router.urls)),
]
