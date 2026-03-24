"""
Home URL Configuration
"""

from django.urls import path
from .views import (
    HomeDataView,
    RecommendedRestaurantsView,
    TrendingView,
    NearbyRestaurantsView,
    SearchSuggestionsView,
    ReorderView,
)

app_name = "home"

urlpatterns = [
    path("", HomeDataView.as_view(), name="home-data"),
    path("recommended/", RecommendedRestaurantsView.as_view(), name="recommended"),
    path("trending/", TrendingView.as_view(), name="trending"),
    path("nearby/", NearbyRestaurantsView.as_view(), name="nearby"),
    path("suggestions/", SearchSuggestionsView.as_view(), name="suggestions"),
    path("reorder/", ReorderView.as_view(), name="reorder"),
]
