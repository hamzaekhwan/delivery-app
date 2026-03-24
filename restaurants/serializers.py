"""
Restaurant Serializers
Updated: Uses lat/lng from request query params instead of is_current address
"""

from rest_framework import serializers
from .models import Restaurant, RestaurantCategory, RestaurantWorkingHours


class RestaurantCategorySerializer(serializers.ModelSerializer):
    restaurants_count = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantCategory
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "icon",
            "image",
            "is_active",
            "order",
            "restaurants_count",
        ]

    def get_restaurants_count(self, obj):
        return obj.restaurants.filter(is_active=True).count()


class RestaurantWorkingHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_display", read_only=True)

    class Meta:
        model = RestaurantWorkingHours
        fields = ["id", "day", "day_name", "opening_time", "closing_time", "is_closed"]


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""

    categories_data = serializers.SerializerMethodField()

    # category_name = serializers.CharField(source="category.name", read_only=True)
    # category_name_en = serializers.CharField(source="category.name_en", read_only=True)
    is_currently_open = serializers.BooleanField(read_only=True)
    current_discount = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    delivery_fee = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "logo",
            "restaurant_type",
            # "category",
            # "category_name",
            # "category_name_en",
            "categories_data",
            "is_active",
            "is_open",
            "is_currently_open",
            "minimum_order_amount",
            "delivery_fee",
            "distance_km",
            "delivery_time_estimate",
            "has_discount",
            "current_discount",
            "average_rating",
            "cover_image",
            "total_reviews",
            "total_orders",
            "is_featured",
        ]

    def _get_user_coordinates(self):
        """
        Get user coordinates from request query params.
        Priority: query params (lat/lng from frontend)
        """
        if not hasattr(self, "_cached_coordinates"):
            self._cached_coordinates = (None, None)

            request = self.context.get("request")
            if not request:
                return self._cached_coordinates

            lat = request.query_params.get("lat")
            lng = request.query_params.get("lng")

            if lat and lng:
                try:
                    self._cached_coordinates = (float(lat), float(lng))
                except (ValueError, TypeError):
                    pass

        return self._cached_coordinates

    def _get_distance(self, obj):
        """Calculate distance between user location and restaurant"""
        user_lat, user_lng = self._get_user_coordinates()

        if user_lat is None:
            return None

        if not obj.latitude or not obj.longitude:
            return None

        from core.utils import calculate_distance

        dist = calculate_distance(
            user_lat,
            user_lng,
            float(obj.latitude),
            float(obj.longitude),
        )
        return round(dist, 2) if dist is not None else None

    def get_distance_km(self, obj):
        return self._get_distance(obj)

    def get_delivery_fee(self, obj):
        distance = self._get_distance(obj)
        if distance is not None:
            from core.utils import calculate_delivery_fee

            return str(calculate_delivery_fee(distance))
        return None

    def get_categories_data(self, obj):
        return [
            {
                "category": c.id,
                "category_name": c.name,
                "category_name_en": c.name_en,
            }
            for c in obj.categories.all()
        ]


class RestaurantDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail views"""

    categories_data = serializers.SerializerMethodField()

    is_currently_open = serializers.BooleanField(read_only=True)
    current_discount = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    working_hours = RestaurantWorkingHoursSerializer(many=True, read_only=True)
    delivery_fee = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "logo",
            "cover_image",
            "restaurant_type",
            "categories_data",
            "address",
            "latitude",
            "longitude",
            "phone",
            "is_active",
            "is_open",
            "is_currently_open",
            "opening_time",
            "closing_time",
            "minimum_order_amount",
            "delivery_fee",
            "distance_km",
            "delivery_time_estimate",
            "has_discount",
            "discount_percentage",
            "current_discount",
            "discount_start_time",
            "discount_end_time",
            "average_rating",
            "total_reviews",
            "total_orders",
            "is_featured",
            "working_hours",
            "created_at",
        ]

    def _get_user_coordinates(self):
        """
        Get user coordinates from request query params.
        """
        if not hasattr(self, "_cached_coordinates"):
            self._cached_coordinates = (None, None)

            request = self.context.get("request")
            if not request:
                return self._cached_coordinates

            lat = request.query_params.get("lat")
            lng = request.query_params.get("lng")

            if lat and lng:
                try:
                    self._cached_coordinates = (float(lat), float(lng))
                except (ValueError, TypeError):
                    pass

        return self._cached_coordinates

    def _get_distance(self, obj):
        user_lat, user_lng = self._get_user_coordinates()

        if user_lat is None:
            return None

        if not obj.latitude or not obj.longitude:
            return None

        from core.utils import calculate_distance

        dist = calculate_distance(
            user_lat,
            user_lng,
            float(obj.latitude),
            float(obj.longitude),
        )
        return round(dist, 2) if dist is not None else None

    def get_distance_km(self, obj):
        return self._get_distance(obj)

    def get_delivery_fee(self, obj):
        distance = self._get_distance(obj)
        if distance is not None:
            from core.utils import calculate_delivery_fee

            return str(calculate_delivery_fee(distance))
        return None

    def get_categories_data(self, obj):
        return [
            {
                "category": c.id,
                "category_name": c.name,
                "category_name_en": c.name_en,
            }
            for c in obj.categories.all()
        ]


class RestaurantMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested use"""

    class Meta:
        model = Restaurant
        fields = ["id", "name", "name_en", "slug", "logo", "restaurant_type"]
