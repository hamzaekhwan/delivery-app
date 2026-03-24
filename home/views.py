"""
Home Views - Homepage Data Aggregation and Recommendations
Updated: All endpoints now support lat/lng filtering for delivery coverage
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import models
from django.db.models import Count, Avg, Q, F, Case, When, Value
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter

from restaurants.models import Restaurant, RestaurantCategory
from restaurants.serializers import (
    RestaurantListSerializer,
    RestaurantCategorySerializer,
)
from menu.models import Product
from menu.serializers import ProductListSerializer
from core.models import Banner
from core.serializers import BannerSerializer
from core.utils import calculate_distance
from core.constants import OrderStatus


# =============================================
# Helper: Filter restaurants by delivery radius
# =============================================


def get_user_coordinates(request):
    """
    Extract and validate lat/lng from query parameters.
    Returns (lat, lng) or (None, None)
    """
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")

    if not lat or not lng:
        return None, None

    try:
        return float(lat), float(lng)
    except (ValueError, TypeError):
        return None, None


def get_max_delivery_radius():
    """
    Get the maximum delivery radius from AppConfiguration.
    Falls back to a default of 15 km.
    """
    try:
        from core.models import AppConfiguration

        config = AppConfiguration.get_config()
        # Use max_delivery_radius_km if available, otherwise default
        return float(getattr(config, "max_delivery_radius_km", 15))
    except Exception:
        return 15.0


def filter_restaurants_by_distance(restaurants, user_lat, user_lng, max_radius=None):
    """
    Filter a queryset of restaurants by distance from user.
    Returns list of (restaurant, distance_km) sorted by distance.

    Each restaurant can have its own delivery_radius_km,
    or we fall back to the global max_delivery_radius_km.
    """
    if max_radius is None:
        max_radius = get_max_delivery_radius()

    results = []
    for restaurant in restaurants:
        if not restaurant.latitude or not restaurant.longitude:
            continue

        distance = calculate_distance(
            user_lat,
            user_lng,
            float(restaurant.latitude),
            float(restaurant.longitude),
        )

        if distance is None:
            continue

        # Use restaurant-specific radius if set, otherwise global
        restaurant_radius = (
            float(restaurant.delivery_radius_km)
            if hasattr(restaurant, "delivery_radius_km")
            and restaurant.delivery_radius_km
            else max_radius
        )

        if distance <= restaurant_radius:
            results.append(
                {
                    "restaurant": restaurant,
                    "distance_km": round(distance, 2),
                }
            )

    results.sort(key=lambda x: x["distance_km"])
    return results


def serialize_restaurants_with_distance(items, request):
    """
    Serialize a list of {restaurant, distance_km} dicts,
    appending distance_km to each serialized restaurant.
    """
    serialized = []
    for item in items:
        data = RestaurantListSerializer(
            item["restaurant"], context={"request": request}
        ).data
        data["distance_km"] = item["distance_km"]
        serialized.append(data)
    return serialized


# =============================================
# Location query parameters for Swagger docs
# =============================================

LOCATION_PARAMS = [
    OpenApiParameter(
        name="lat", description="User latitude", required=False, type=float
    ),
    OpenApiParameter(
        name="lng", description="User longitude", required=False, type=float
    ),
]


# =============================================
# Views
# =============================================


class HomeDataView(APIView):
    """
    Get all homepage data in a single request.
    If lat/lng provided, restaurants are filtered by delivery coverage.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Home"],
        summary="Get homepage data",
        description="Returns banners, categories, featured restaurants, popular items, and more. "
        "Pass lat/lng to filter restaurants by delivery coverage area.",
        parameters=LOCATION_PARAMS,
    )
    def get(self, request):
        user_lat, user_lng = get_user_coordinates(request)
        has_location = user_lat is not None
        today = timezone.now().date()

        # Active banners (no location filtering needed)
        banners = (
            Banner.objects.filter(is_active=True, start_date__date__lte=today)
            .filter(Q(end_date__isnull=True) | Q(end_date__date__gte=today))
            .order_by("order")[:10]
        )
        # Restaurant categories (no location filtering needed)
        categories = RestaurantCategory.objects.filter(is_active=True).order_by(
            "order"
        )[:20]

        # ---- Featured restaurants ----
        featured_qs = (
            Restaurant.objects.filter(is_active=True, is_featured=True)
            .prefetch_related("categories")
            .annotate(
                _is_open_now=Case(
                    When(is_open=True, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField(),
                ),
                _has_active_discount=Case(
                    When(has_discount=True, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField(),
                ),
            )
            .order_by("-_is_open_now", "-_has_active_discount")
        )

        if has_location:
            featured_items = filter_restaurants_by_distance(
                featured_qs, user_lat, user_lng
            )[:10]
            featured_data = serialize_restaurants_with_distance(featured_items, request)
        else:
            featured_data = RestaurantListSerializer(
                featured_qs[:10], many=True, context={"request": request}
            ).data

        # ---- Popular restaurants ----
        popular_qs = (
            Restaurant.objects.filter(is_active=True)
            .prefetch_related("categories")
            .order_by("-total_orders")
        )

        if has_location:
            popular_items = filter_restaurants_by_distance(
                popular_qs, user_lat, user_lng
            )[:10]
            popular_data = serialize_restaurants_with_distance(popular_items, request)
        else:
            popular_data = RestaurantListSerializer(
                popular_qs[:10], many=True, context={"request": request}
            ).data

        # ---- New restaurants (أحدث المطاعم) ----
        new_qs = (
            Restaurant.objects.filter(is_active=True)
            .prefetch_related("categories")
            .order_by("-created_at")
        )

        if has_location:
            new_items = filter_restaurants_by_distance(new_qs, user_lat, user_lng)
            # Re-sort by creation date (newest first), not distance
            new_items.sort(
                key=lambda x: x["restaurant"].created_at, reverse=True
            )
            new_items = new_items[:5]
            new_data = serialize_restaurants_with_distance(new_items, request)
        else:
            new_data = RestaurantListSerializer(
                new_qs[:5], many=True, context={"request": request}
            ).data

        # ---- Discount restaurants ----
        discount_qs = (
            Restaurant.objects.filter(
                is_active=True,
                has_discount=True,
                discount_start_time__lte=timezone.now().time(),
                discount_end_time__gte=timezone.now().time(),
            )
            .prefetch_related("categories")
            .order_by("-discount_percentage")
        )

        if has_location:
            discount_items = filter_restaurants_by_distance(
                discount_qs, user_lat, user_lng
            )[:10]
            discount_data = serialize_restaurants_with_distance(discount_items, request)
        else:
            discount_data = RestaurantListSerializer(
                discount_qs[:10], many=True, context={"request": request}
            ).data

        # ---- Popular products (filter by restaurant coverage) ----
        popular_products_qs = (
            Product.objects.filter(
                is_available=True, restaurant__is_active=True, has_discount=True
            )
            .select_related("restaurant", "category")
            .order_by("-created_at")
        )

        if has_location:
            # Filter products whose restaurant is within delivery range
            max_radius = get_max_delivery_radius()
            filtered_products = []
            for product in popular_products_qs[:50]:  # check up to 50
                r = product.restaurant
                if not r.latitude or not r.longitude:
                    continue
                distance = calculate_distance(
                    user_lat, user_lng, float(r.latitude), float(r.longitude)
                )
                if distance is not None and distance <= max_radius:
                    filtered_products.append(product)
                if len(filtered_products) >= 10:
                    break
            popular_products_data = ProductListSerializer(
                filtered_products, many=True
            ).data
        else:
            popular_products_data = ProductListSerializer(
                popular_products_qs[:10], many=True
            ).data

        return Response(
            {
                "banners": BannerSerializer(banners, many=True).data,
                "categories": RestaurantCategorySerializer(categories, many=True).data,
                "featured_restaurants": featured_data,
                "popular_restaurants": popular_data,
                "new_restaurants": new_data,
                "discount_restaurants": discount_data,
                "popular_products": popular_products_data,
                "user_location_applied": has_location,
            }
        )


class RecommendedRestaurantsView(APIView):
    """
    Get personalized restaurant recommendations, filtered by delivery area.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Home"],
        summary="Get recommended restaurants",
        description="Personalized recommendations filtered by delivery coverage.",
        parameters=LOCATION_PARAMS,
    )
    def get(self, request):
        user_lat, user_lng = get_user_coordinates(request)
        has_location = user_lat is not None

        recommendations_qs = (
            Restaurant.objects.filter(is_active=True)
            .prefetch_related("categories")
            .order_by("-total_orders", "-average_rating")
        )

        if has_location:
            items = filter_restaurants_by_distance(
                recommendations_qs, user_lat, user_lng
            )[:15]
            data = serialize_restaurants_with_distance(items, request)
        else:
            data = RestaurantListSerializer(
                recommendations_qs[:15], many=True, context={"request": request}
            ).data

        return Response({"recommendations": data})


class TrendingView(APIView):
    """
    Get trending restaurants, filtered by delivery area.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Home"],
        summary="Get trending items",
        description="Trending restaurants in the last 24 hours, filtered by delivery coverage.",
        parameters=LOCATION_PARAMS,
    )
    def get(self, request):
        user_lat, user_lng = get_user_coordinates(request)
        has_location = user_lat is not None

        trending_qs = (
            Restaurant.objects.filter(
                is_active=True,
                orders__created_at__gte=timezone.now() - timedelta(hours=24),
            )
            .annotate(recent_orders=Count("orders"))
            .order_by("-recent_orders")
        )

        if has_location:
            items = filter_restaurants_by_distance(trending_qs, user_lat, user_lng)[:10]
            data = serialize_restaurants_with_distance(items, request)
        else:
            data = RestaurantListSerializer(
                trending_qs[:10], many=True, context={"request": request}
            ).data

        return Response({"trending_restaurants": data})


class NearbyRestaurantsView(APIView):
    """
    Get restaurants near user's location (uses same delivery coverage logic).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Home"],
        summary="Get nearby restaurants",
        description="Restaurants within delivery range of the provided coordinates.",
        parameters=LOCATION_PARAMS
        + [
            OpenApiParameter(
                name="radius",
                description="Max radius in km (overrides global config)",
                required=False,
                type=float,
            ),
        ],
    )
    def get(self, request):
        user_lat, user_lng = get_user_coordinates(request)

        if user_lat is None:
            return Response(
                {"error": "lat and lng parameters are required"}, status=400
            )

        # Allow custom radius override, otherwise use global config
        custom_radius = request.query_params.get("radius")
        if custom_radius:
            try:
                max_radius = float(custom_radius)
            except ValueError:
                max_radius = get_max_delivery_radius()
        else:
            max_radius = get_max_delivery_radius()

        restaurants_qs = Restaurant.objects.filter(
            is_active=True, latitude__isnull=False, longitude__isnull=False
        ).prefetch_related("categories")

        items = filter_restaurants_by_distance(
            restaurants_qs, user_lat, user_lng, max_radius
        )[:20]
        data = serialize_restaurants_with_distance(items, request)

        return Response({"restaurants": data})


class SearchSuggestionsView(APIView):
    """
    Get search suggestions, optionally filtered by delivery coverage.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Home"],
        summary="Get search suggestions",
        parameters=LOCATION_PARAMS
        + [
            OpenApiParameter(
                name="q", description="Search query", required=True, type=str
            ),
        ],
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if len(query) < 2:
            return Response({"suggestions": []})

        user_lat, user_lng = get_user_coordinates(request)
        has_location = user_lat is not None

        # Search restaurants
        restaurants_qs = Restaurant.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(name_en__icontains=query)
        )

        if has_location:
            nearby_items = filter_restaurants_by_distance(
                restaurants_qs, user_lat, user_lng
            )[:5]
            restaurant_suggestions = [
                {
                    "id": item["restaurant"].id,
                    "name": item["restaurant"].name,
                    "type": "restaurant",
                    "distance_km": item["distance_km"],
                }
                for item in nearby_items
            ]
        else:
            restaurant_suggestions = [
                {"id": r.id, "name": r.name, "type": "restaurant"}
                for r in restaurants_qs[:5]
            ]

        # Search products (filter by nearby restaurants if location provided)
        products_qs = (
            Product.objects.filter(is_available=True, restaurant__is_active=True)
            .filter(Q(name__icontains=query) | Q(name_en__icontains=query))
            .select_related("restaurant")
        )

        if has_location:
            max_radius = get_max_delivery_radius()
            product_suggestions = []
            for p in products_qs[:20]:
                r = p.restaurant
                if not r.latitude or not r.longitude:
                    continue
                distance = calculate_distance(
                    user_lat, user_lng, float(r.latitude), float(r.longitude)
                )
                if distance is not None and distance <= max_radius:
                    product_suggestions.append(
                        {
                            "id": p.id,
                            "name": p.name,
                            "restaurant": r.name,
                            "type": "product",
                        }
                    )
                if len(product_suggestions) >= 5:
                    break
        else:
            product_suggestions = [
                {
                    "id": p.id,
                    "name": p.name,
                    "restaurant": p.restaurant.name,
                    "type": "product",
                }
                for p in products_qs[:5]
            ]

        # Categories (no location filter)
        categories = RestaurantCategory.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(name_en__icontains=query)
        )[:3]

        return Response(
            {
                "suggestions": {
                    "restaurants": restaurant_suggestions,
                    "products": product_suggestions,
                    "categories": [
                        {"id": c.id, "name": c.name, "type": "category"}
                        for c in categories
                    ],
                }
            }
        )


class ReorderView(APIView):
    """
    Get user's recent orders for quick reorder
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Home"],
        summary="Get reorder suggestions",
        description="Recent orders for quick reordering",
    )
    def get(self, request):
        from orders.models import Order

        recent_orders = (
            Order.objects.filter(user=request.user, status="delivered")
            .select_related("restaurant")
            .prefetch_related("items__product")
            .order_by("-delivered_at")[:5]
        )

        reorder_suggestions = []
        for order in recent_orders:
            items = [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name
                    if item.product
                    else item.product_name,
                    "quantity": item.quantity,
                }
                for item in order.items.all()[:3]
            ]

            reorder_suggestions.append(
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "restaurant_id": order.restaurant_id,
                    "restaurant_name": order.restaurant.name,
                    "restaurant_logo": order.restaurant.logo.url
                    if order.restaurant.logo
                    else None,
                    "total": str(order.total),
                    "items_preview": items,
                    "ordered_at": order.created_at,
                }
            )

        return Response({"reorder_suggestions": reorder_suggestions})
