"""
Reviews Serializers
"""

from rest_framework import serializers
from .models import RestaurantReview, RestaurantReviewImage, DriverReview


class RestaurantReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantReviewImage
        fields = ["id", "image", "order"]
        read_only_fields = ["id"]


class RestaurantReviewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing reviews"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    images = RestaurantReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = RestaurantReview
        fields = [
            "id",
            "user_name",
            "overall_rating",
            "food_quality_rating",
            "packaging_rating",
            "value_rating",
            "comment",
            "images",
            "restaurant_response",
            "restaurant_response_at",
            "created_at",
        ]


class RestaurantReviewDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for a single review"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    images = RestaurantReviewImageSerializer(many=True, read_only=True)

    class Meta:
        model = RestaurantReview
        fields = [
            "id",
            "order_number",
            "restaurant_name",
            "user_name",
            "overall_rating",
            "food_quality_rating",
            "packaging_rating",
            "value_rating",
            "comment",
            "images",
            "restaurant_response",
            "restaurant_response_at",
            "created_at",
        ]


class CreateRestaurantReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating a restaurant review"""

    images = serializers.ListField(
        child=serializers.ImageField(), required=False, write_only=True, max_length=5
    )

    class Meta:
        model = RestaurantReview
        fields = [
            "order",
            "overall_rating",
            "food_quality_rating",
            "packaging_rating",
            "value_rating",
            "comment",
            "images",
        ]

    def validate_order(self, value):
        user = self.context["request"].user

        # Check if order belongs to user
        if value.user != user:
            raise serializers.ValidationError("This order does not belong to you.")

        # Check if order is delivered
        if value.status != "delivered":
            raise serializers.ValidationError("You can only review delivered orders.")

        # Check if already reviewed
        if hasattr(value, "restaurant_review"):
            raise serializers.ValidationError("You have already reviewed this order.")

        return value

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        order = validated_data["order"]

        review = RestaurantReview.objects.create(
            user=self.context["request"].user,
            restaurant=order.restaurant,
            **validated_data,
        )

        # Create review images
        for i, image in enumerate(images_data):
            RestaurantReviewImage.objects.create(review=review, image=image, order=i)

        return review


class DriverReviewListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing driver reviews"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = DriverReview
        fields = [
            "id",
            "user_name",
            "overall_rating",
            "comment",
            "created_at",
        ]


class DriverReviewDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for driver reviews"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    driver_name = serializers.CharField(source="driver.full_name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = DriverReview
        fields = [
            "id",
            "order_number",
            "driver_name",
            "user_name",
            "overall_rating",
            "comment",
            "created_at",
        ]


class CreateDriverReviewSerializer(serializers.ModelSerializer):
    """Serializer for creating a driver review"""

    class Meta:
        model = DriverReview
        fields = ["order", "overall_rating", "comment"]

    def validate_order(self, value):
        user = self.context["request"].user

        # Check if order belongs to user
        if value.user != user:
            raise serializers.ValidationError("This order does not belong to you.")

        # Check if order is delivered
        if value.status != "delivered":
            raise serializers.ValidationError("You can only review delivered orders.")

        # Check if order had a driver
        if not value.driver:
            raise serializers.ValidationError(
                "This order did not have a driver assigned."
            )

        # Check if already reviewed
        if hasattr(value, "driver_review"):
            raise serializers.ValidationError(
                "You have already reviewed the driver for this order."
            )

        return value

    def create(self, validated_data):
        order = validated_data["order"]

        review = DriverReview.objects.create(
            user=self.context["request"].user, driver=order.driver, **validated_data
        )

        return review


class ReviewStatsSerializer(serializers.Serializer):
    """Serializer for review statistics"""

    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    rating_distribution = serializers.DictField()

    # Detailed averages (restaurant reviews only)
    avg_food_quality = serializers.FloatField(required=False)
    avg_packaging = serializers.FloatField(required=False)
    avg_value = serializers.FloatField(required=False)
