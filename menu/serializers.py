"""
Menu Serializers
"""

from rest_framework import serializers
from .models import (
    MenuCategory,
    MenuSubCategory,
    Product,
    ProductVariation,
    ProductAddon,
    ProductImage,
)


class MenuSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuSubCategory
        fields = ["id", "name", "name_en", "slug", "is_active", "order"]


class MenuCategorySerializer(serializers.ModelSerializer):
    subcategories = MenuSubCategorySerializer(many=True, read_only=True)
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = MenuCategory
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "image",
            "is_active",
            "order",
            "subcategories",
            "products_count",
        ]

    def get_products_count(self, obj):
        return obj.products.filter(is_available=True).count()


class ProductVariationSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = ProductVariation
        fields = [
            "id",
            "name",
            "name_en",
            "price_adjustment",
            "total_price",
            "is_available",
            "order",
        ]


class ProductAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAddon
        fields = [
            "id",
            "name",
            "name_en",
            "price",
            "is_available",
            "max_quantity",
            "order",
        ]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "order"]


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""

    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    # Override: return True if ANY discount (product or restaurant)
    has_discount = serializers.BooleanField(source="has_any_discount", read_only=True)
    is_discount_active = serializers.BooleanField(
        source="has_any_discount", read_only=True
    )
    effective_discount_source = serializers.CharField(read_only=True, allow_null=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "category",
            "category_name",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "image",
            "base_price",
            "current_price",
            "discount_amount",
            "has_discount",
            "is_discount_active",
            "effective_discount_source",
            "is_available",
            "is_featured",
            "is_popular",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail views"""

    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    # Override: return True if ANY discount (product or restaurant)
    has_discount = serializers.BooleanField(source="has_any_discount", read_only=True)
    is_discount_active = serializers.BooleanField(
        source="has_any_discount", read_only=True
    )
    effective_discount_source = serializers.CharField(read_only=True, allow_null=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_name = serializers.CharField(
        source="subcategory.name", read_only=True, allow_null=True
    )
    variations = ProductVariationSerializer(many=True, read_only=True)
    addons = ProductAddonSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "category",
            "category_name",
            "subcategory",
            "subcategory_name",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "image",
            "base_price",
            "current_price",
            "discount_amount",
            "has_discount",
            "discount_type",
            "discount_value",
            "is_discount_active",
            "effective_discount_source",
            "discount_start",
            "discount_end",
            "calories",
            "preparation_time",
            "is_available",
            "is_featured",
            "is_popular",
            "variations",
            "addons",
            "images",
            "created_at",
        ]


class MenuCategoryWithProductsSerializer(serializers.ModelSerializer):
    """Category with all products for menu display"""

    products = ProductListSerializer(many=True, read_only=True)
    subcategories = MenuSubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = MenuCategory
        fields = [
            "id",
            "name",
            "name_en",
            "slug",
            "description",
            "description_en",
            "image",
            "is_active",
            "order",
            "subcategories",
            "products",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Only show available products
        data["products"] = [p for p in data["products"] if p.get("is_available")]
        return data


class ProductMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for cart/order items"""

    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    has_discount = serializers.BooleanField(source="has_any_discount", read_only=True)
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_en",
            "image",
            "base_price",
            "current_price",
            "has_discount",
            "discount_amount",
        ]
