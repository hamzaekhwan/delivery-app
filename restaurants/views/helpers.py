"""
Restaurant Views - Shared helpers
"""

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter

from ..serializers import RestaurantListSerializer
from core.utils import calculate_distance, build_arabic_search_pattern


LOCATION_PARAMS = [
    OpenApiParameter(name="lat", description="خط العرض", required=False, type=float),
    OpenApiParameter(name="lng", description="خط الطول", required=False, type=float),
]


def get_user_coordinates(request):
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    if not lat or not lng:
        return None, None
    try:
        return float(lat), float(lng)
    except (ValueError, TypeError):
        return None, None


def get_max_delivery_radius():
    try:
        from core.models import AppConfiguration

        config = AppConfiguration.get_config()
        return float(getattr(config, "max_delivery_radius_km", 15))
    except Exception:
        return 15.0


def filter_restaurants_by_distance(restaurants, user_lat, user_lng, max_radius=None):
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
    serialized = []
    for item in items:
        data = RestaurantListSerializer(
            item["restaurant"], context={"request": request}
        ).data
        data["distance_km"] = item["distance_km"]
        serialized.append(data)
    return serialized


def build_arabic_search_q(search_text, fields):
    """
    بناء Q object للبحث العربي باستخدام regex.
    fields: قائمة بأسماء الحقول المراد البحث فيها
    يبحث بالنص الأصلي (للإنجليزي) وبـ regex pattern (للعربي)
    """
    pattern = build_arabic_search_pattern(search_text)
    q = Q()
    for field in fields:
        if field.endswith("_en"):
            # الحقول الإنجليزية — icontains عادي
            q |= Q(**{f"{field}__icontains": search_text})
        else:
            # الحقول العربية — regex pattern
            q |= Q(**{f"{field}__iregex": pattern})
    return q
