"""
Coupon Serializers
"""

from rest_framework import serializers
from .models import Coupon, CouponUsage


class CouponSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    restaurant_name = serializers.CharField(
        source="restaurant.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "description_en",
            "discount_type",
            "discount_value",
            "max_discount",
            "start_date",
            "end_date",
            "minimum_order_amount",
            "restaurant",
            "restaurant_name",
            "first_order_only",
            "status",
            "is_valid",
        ]


class CouponValidationSerializer(serializers.Serializer):
    """Serializer for coupon validation request"""

    code = serializers.CharField(max_length=50)
    restaurant_id = serializers.IntegerField(required=False)
    order_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )


class CouponValidationResponseSerializer(serializers.Serializer):
    """Serializer for coupon validation response"""

    valid = serializers.BooleanField()
    coupon = CouponSerializer(required=False)
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    message = serializers.CharField(required=False)


class CouponUsageSerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)

    class Meta:
        model = CouponUsage
        fields = [
            "id",
            "coupon",
            "coupon_code",
            "order",
            "discount_amount",
            "created_at",
        ]
