"""
Cart Serializers - Updated for multiple carts support
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import Cart, CartItem, CartItemAddon, CART_MAX_PER_USER
from menu.serializers import (
    ProductMinimalSerializer,
    ProductVariationSerializer,
    ProductAddonSerializer,
)
from restaurants.serializers import RestaurantMinimalSerializer


# ═══════════════════════════════════════════════════════════
#                    Addon Serializer
# ═══════════════════════════════════════════════════════════
class CartItemAddonSerializer(serializers.ModelSerializer):
    addon_name = serializers.CharField(source="addon.name", read_only=True)
    addon_price = serializers.DecimalField(
        source="addon.price", max_digits=10, decimal_places=2, read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItemAddon
        fields = ["id", "addon", "addon_name", "addon_price", "quantity", "total_price"]


# ═══════════════════════════════════════════════════════════
#                    Cart Item Serializer
# ═══════════════════════════════════════════════════════════
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductMinimalSerializer(read_only=True)
    variation = ProductVariationSerializer(read_only=True)
    cart_item_addons = CartItemAddonSerializer(many=True, read_only=True)
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    addons_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "variation",
            "quantity",
            "special_instructions",
            "unit_price",
            "addons_total",
            "total_price",
            "cart_item_addons",
            "created_at",
        ]


# ═══════════════════════════════════════════════════════════
#                    Full Cart Serializer
# ═══════════════════════════════════════════════════════════
class CartSerializer(serializers.ModelSerializer):
    restaurant = RestaurantMinimalSerializer(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    delivery_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    coupon_code = serializers.CharField(
        source="coupon.code", read_only=True, allow_null=True
    )

    # New fields for expiry
    is_expired = serializers.BooleanField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "restaurant",
            "items",
            "items_count",
            "coupon",
            "coupon_code",
            "notes",
            "subtotal",
            "delivery_fee",
            "discount_amount",
            "total",
            "expires_at",
            "is_expired",
            "time_remaining_seconds",
            "created_at",
            "updated_at",
        ]

    def get_time_remaining_seconds(self, obj):
        """Get remaining time in seconds"""
        remaining = obj.time_remaining
        return max(0, int(remaining.total_seconds()))


# ═══════════════════════════════════════════════════════════
#                    Cart List Serializer (Minimal)
# ═══════════════════════════════════════════════════════════
class CartListSerializer(serializers.ModelSerializer):
    """
    Lighter serializer for listing multiple carts
    """

    restaurant_id = serializers.IntegerField(source="restaurant.id", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_name_en = serializers.CharField(
        source="restaurant.name_en", read_only=True
    )
    restaurant_logo = serializers.ImageField(source="restaurant.logo", read_only=True)

    items_count = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    # Preview of items (first 3)
    items_preview = serializers.SerializerMethodField()

    # Expiry info
    expires_at = serializers.DateTimeField(read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "restaurant_id",
            "restaurant_name",
            "restaurant_name_en",
            "restaurant_logo",
            "items_count",
            "total",
            "items_preview",
            "expires_at",
            "time_remaining_seconds",
            "created_at",
            "updated_at",
        ]

    def get_items_preview(self, obj):
        """Get preview of first 3 items"""
        items = obj.items.all()[:3]
        return [
            {
                "id": item.id,
                "product_name": item.product.name,
                "product_name_en": item.product.name_en,
                "quantity": item.quantity,
                "total_price": str(item.total_price),
            }
            for item in items
        ]

    def get_time_remaining_seconds(self, obj):
        """Get remaining time in seconds"""
        remaining = obj.time_remaining
        return max(0, int(remaining.total_seconds()))


# ═══════════════════════════════════════════════════════════
#                    Input Serializers
# ═══════════════════════════════════════════════════════════
class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart"""

    restaurant_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    variation_id = serializers.IntegerField(required=False, allow_null=True)
    addons = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    special_instructions = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_restaurant_id(self, value):
        from restaurants.models import Restaurant

        try:
            restaurant = Restaurant.objects.get(id=value, is_active=True)
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError("المطعم غير موجود")
        return value

    def validate_product_id(self, value):
        from menu.models import Product

        try:
            product = Product.objects.get(id=value, is_available=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("المنتج غير متوفر")
        return value

    def validate(self, data):
        from menu.models import Product

        product = Product.objects.get(id=data["product_id"])

        # Validate product belongs to restaurant
        if product.restaurant_id != data["restaurant_id"]:
            raise serializers.ValidationError("المنتج لا ينتمي لهذا المطعم")

        # Validate variation
        if data.get("variation_id"):
            from menu.models import ProductVariation

            try:
                variation = ProductVariation.objects.get(
                    id=data["variation_id"], product=product, is_available=True
                )
            except ProductVariation.DoesNotExist:
                raise serializers.ValidationError("التنويع غير متوفر")

        # Validate addons
        if data.get("addons"):
            from menu.models import ProductAddon

            for addon_data in data["addons"]:
                addon_id = addon_data.get("addon_id")
                quantity = addon_data.get("quantity", 1)

                try:
                    addon = ProductAddon.objects.get(
                        id=addon_id, product=product, is_available=True
                    )
                    if quantity > addon.max_quantity:
                        raise serializers.ValidationError(
                            f"الحد الأقصى للإضافة {addon.name} هو {addon.max_quantity}"
                        )
                except ProductAddon.DoesNotExist:
                    raise serializers.ValidationError("إضافة غير متوفرة")

        return data


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item"""

    quantity = serializers.IntegerField(min_value=0)
    special_instructions = serializers.CharField(required=False, allow_blank=True)


class ApplyCouponSerializer(serializers.Serializer):
    """Serializer for applying coupon"""

    code = serializers.CharField(max_length=50)
