"""
Menu Views - API endpoints for menu
"""

from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db import models
from .models import MenuCategory, Product, ProductVariation, ProductAddon
from .serializers import (
    MenuCategorySerializer,
    MenuCategoryWithProductsSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductVariationSerializer,
    ProductAddonSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="تصنيفات القائمة",
        description="الحصول على تصنيفات قائمة مطعم معين",
        tags=["Menu"],
        parameters=[
            OpenApiParameter(
                name="restaurant", description="معرف المطعم", required=True, type=int
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="تفاصيل تصنيف",
        description="الحصول على تفاصيل تصنيف مع منتجاته",
        tags=["Menu"],
    ),
)
class MenuCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for menu categories
    """

    serializer_class = MenuCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["restaurant", "is_active"]

    def get_queryset(self):
        queryset = MenuCategory.objects.filter(is_active=True)
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset.prefetch_related("subcategories", "products")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MenuCategoryWithProductsSerializer
        return MenuCategorySerializer


@extend_schema_view(
    list=extend_schema(
        summary="قائمة المنتجات",
        description="الحصول على المنتجات مع إمكانية الفلترة",
        tags=["Menu"],
        parameters=[
            OpenApiParameter(
                name="restaurant", description="معرف المطعم", required=False, type=int
            ),
            OpenApiParameter(
                name="category", description="معرف التصنيف", required=False, type=int
            ),
            OpenApiParameter(
                name="has_discount",
                description="المنتجات التي لديها خصم",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="is_featured",
                description="المنتجات المميزة",
                required=False,
                type=bool,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="تفاصيل منتج", description="الحصول على تفاصيل منتج معين", tags=["Menu"]
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for products
    """

    permission_classes = [AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "restaurant",
        "category",
        "subcategory",
        "is_available",
        "has_discount",
        "is_featured",
        "is_popular",
    ]
    search_fields = ["name", "name_en", "description"]
    ordering_fields = ["name", "base_price", "order", "created_at"]
    ordering = ["order", "-is_featured", "name"]
    lookup_field = "slug"

    def get_queryset(self):
        return Product.objects.filter(
            is_available=True, restaurant__is_active=True
        ).select_related("restaurant", "category", "subcategory")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    @extend_schema(
        summary="المنتجات المميزة",
        description="الحصول على المنتجات المميزة لمطعم معين",
        tags=["Menu"],
    )
    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured products"""
        restaurant_id = request.query_params.get("restaurant")
        queryset = self.get_queryset().filter(is_featured=True)

        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        serializer = ProductListSerializer(queryset[:20], many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="المنتجات الشائعة",
        description="الحصول على المنتجات الشائعة",
        tags=["Menu"],
    )
    @action(detail=False, methods=["get"])
    def popular(self, request):
        """Get popular products"""
        restaurant_id = request.query_params.get("restaurant")
        queryset = self.get_queryset().filter(is_popular=True)

        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        serializer = ProductListSerializer(queryset[:20], many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="العروض والخصومات",
        description="الحصول على المنتجات التي عليها خصم",
        tags=["Menu"],
    )
    @action(detail=False, methods=["get"])
    def deals(self, request):
        """Get products with active discounts"""
        restaurant_id = request.query_params.get("restaurant")
        queryset = self.get_queryset().filter(has_discount=True)

        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        # Filter only active discounts
        from django.utils import timezone

        now = timezone.now()
        queryset = queryset.filter(
            models.Q(discount_start__isnull=True) | models.Q(discount_start__lte=now),
            models.Q(discount_end__isnull=True) | models.Q(discount_end__gte=now),
        )

        serializer = ProductListSerializer(queryset[:20], many=True)
        return Response(serializer.data)


@extend_schema(
    summary="تنويعات المنتج", description="الحصول على تنويعات منتج معين", tags=["Menu"]
)
class ProductVariationsView(generics.ListAPIView):
    """Get variations for a product"""

    serializer_class = ProductVariationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs.get("product_id")
        return ProductVariation.objects.filter(product_id=product_id, is_available=True)


@extend_schema(
    summary="إضافات المنتج", description="الحصول على إضافات منتج معين", tags=["Menu"]
)
class ProductAddonsView(generics.ListAPIView):
    """Get addons for a product"""

    serializer_class = ProductAddonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs.get("product_id")
        return ProductAddon.objects.filter(product_id=product_id, is_available=True)
