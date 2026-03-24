"""
User Order Views - Order CRUD for customers
"""

from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import Order
from ..serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CreateOrderSerializer,
    CancelOrderSerializer,
)
from core.constants import OrderStatus


# ============================================
# USER ORDER APIs
# ============================================


@extend_schema_view(
    list=extend_schema(summary="قائمة الطلبات", tags=["User - Orders"]),
    retrieve=extend_schema(summary="تفاصيل الطلب", tags=["User - Orders"]),
)
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("restaurant", "driver", "coupon")
            .prefetch_related("items", "status_history")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderDetailSerializer

    @extend_schema(summary="الطلبات النشطة", tags=["User - Orders"])
    @action(detail=False, methods=["get"])
    def active(self, request):
        orders = self.get_queryset().exclude(
            status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED]
        )
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(summary="سجل الطلبات", tags=["User - Orders"])
    @action(detail=False, methods=["get"])
    def history(self, request):
        orders = self.get_queryset().filter(
            status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED]
        )
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(summary="تتبع الطلب", tags=["User - Orders"])
    @action(detail=True, methods=["get"])
    def track(self, request, pk=None):
        order = self.get_object()
        return Response(order.get_tracking_info())


@extend_schema(
    summary="إنشاء طلب",
    tags=["User - Orders"],
    request=CreateOrderSerializer,
    responses={201: OrderDetailSerializer},
)
class CreateOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED
        )


@extend_schema(
    summary="تأكيد الطلب",
    tags=["User - Orders"],
    responses={200: OrderDetailSerializer},
)
class PlaceOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(
            Order, id=order_id, user=request.user, status=OrderStatus.DRAFT
        )
        success, error = order.place_order()
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)


@extend_schema(
    summary="إلغاء الطلب",
    tags=["User - Orders"],
    request=CancelOrderSerializer,
    responses={200: OrderDetailSerializer},
)
class CancelOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        serializer = CancelOrderSerializer(data=request.data, context={"order": order})
        serializer.is_valid(raise_exception=True)
        success, error = order.update_status(
            OrderStatus.CANCELLED,
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)


@extend_schema(summary="إعادة الطلب", tags=["User - Orders"])
class ReorderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        from cart.models import Cart, CartItem, CartItemAddon
        from menu.models import Product, ProductVariation, ProductAddon

        order = get_object_or_404(
            Order, id=order_id, user=request.user, status=OrderStatus.DELIVERED
        )

        if not order.restaurant.is_active:
            return Response(
                {"error": "المطعم غير متاح حالياً"}, status=status.HTTP_400_BAD_REQUEST
            )

        cart, _ = Cart.objects.get_or_create(
            user=request.user, restaurant=order.restaurant
        )
        cart.clear()
        errors = []

        for item in order.items.all():
            try:
                product = Product.objects.get(id=item.product_id, is_available=True)
            except Product.DoesNotExist:
                errors.append(f"{item.product_snapshot.get('name', 'منتج')} غير متوفر")
                continue

            variation = None
            if item.variation_id:
                try:
                    variation = ProductVariation.objects.get(
                        id=item.variation_id, is_available=True
                    )
                except ProductVariation.DoesNotExist:
                    pass

            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                variation=variation,
                quantity=item.quantity,
                special_instructions=item.special_instructions,
                price_snapshot=product.current_price
                + (variation.price_adjustment if variation else 0),
            )

            for addon_item in item.order_item_addons.all():
                try:
                    addon = ProductAddon.objects.get(
                        id=addon_item.addon_id, is_available=True
                    )
                    CartItemAddon.objects.create(
                        cart_item=cart_item, addon=addon, quantity=addon_item.quantity
                    )
                except ProductAddon.DoesNotExist:
                    pass

        if errors and not cart.items.exists():
            return Response(
                {"error": "جميع المنتجات غير متوفرة", "details": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from cart.serializers import CartSerializer

        return Response(
            {"cart": CartSerializer(cart).data, "warnings": errors if errors else None},
            status=status.HTTP_200_OK,
        )
