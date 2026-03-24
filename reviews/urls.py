"""
Reviews URL Configuration
"""

from django.urls import path
from .views import (
    RestaurantReviewsView,
    RestaurantReviewStatsView,
    CreateRestaurantReviewView,
    DriverReviewsView,
    DriverReviewStatsView,
    CreateDriverReviewView,
    UserReviewsView,
    PendingReviewsView,
)

app_name = "reviews"

urlpatterns = [
    # Restaurant reviews
    path(
        "restaurants/<int:restaurant_id>/",
        RestaurantReviewsView.as_view(),
        name="restaurant-reviews",
    ),
    path(
        "restaurants/<int:restaurant_id>/stats/",
        RestaurantReviewStatsView.as_view(),
        name="restaurant-review-stats",
    ),
    path(
        "restaurant/create/",
        CreateRestaurantReviewView.as_view(),
        name="create-restaurant-review",
    ),
    # Driver reviews
    path(
        "drivers/<int:driver_id>/", DriverReviewsView.as_view(), name="driver-reviews"
    ),
    path(
        "drivers/<int:driver_id>/stats/",
        DriverReviewStatsView.as_view(),
        name="driver-review-stats",
    ),
    path(
        "driver/create/", CreateDriverReviewView.as_view(), name="create-driver-review"
    ),
    # User reviews
    path("my-reviews/", UserReviewsView.as_view(), name="user-reviews"),
    path("pending/", PendingReviewsView.as_view(), name="pending-reviews"),
]
