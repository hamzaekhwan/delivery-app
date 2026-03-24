"""
Driver Order Views - Order management for drivers
"""

from rest_framework import viewsets, views, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import Order, DriverOrderRequest
from ..serializers import (
    OrderDetailSerializer,
    UpdateOrderStatusSerializer,
    DriverOrderRequestSerializer,
    RejectOrderRequestSerializer,
    DriverOrderListSerializer,
    DriverOrderDetailSerializer,
    DriverUpdateOrderStatusSerializer,
    DriverSetOrderPriceSerializer,
    CreateDeliveryReportSerializer,
    OrderDeliveryReportSerializer,
)
from core.constants import OrderStatus, DriverOrderAction


# ============================================
# DRIVER ORDER APIs
# ============================================


@extend_schema(
    summary="طلبات السائق الجديدة",
    tags=["Driver - Orders"],
    responses={200: DriverOrderRequestSerializer(many=True)},
)
class DriverPendingRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DriverOrderRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != "driver":
            return DriverOrderRequest.objects.none()
        return DriverOrderRequest.objects.filter(
            driver=user,
            action=DriverOrderAction.PENDING,
            order__status=OrderStatus.PREPARING,
        ).select_related("order", "order__restaurant")


@extend_schema(
    summary="قبول طلب التوصيل",
    tags=["Driver - Orders"],
    responses={200: DriverOrderRequestSerializer},
)
class AcceptOrderRequestView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "driver":
            return Response(
                {"error": "هذه الخدمة للسائقين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        order_request = get_object_or_404(
            DriverOrderRequest, id=request_id, driver=request.user
        )
        success, error = order_request.accept()
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DriverOrderRequestSerializer(order_request).data)


@extend_schema(
    summary="رفض طلب التوصيل",
    tags=["Driver - Orders"],
    request=RejectOrderRequestSerializer,
    responses={200: DriverOrderRequestSerializer},
)
class RejectOrderRequestView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        if request.user.role != "driver":
            return Response(
                {"error": "هذه الخدمة للسائقين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        order_request = get_object_or_404(
            DriverOrderRequest, id=request_id, driver=request.user
        )
        serializer = RejectOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        success, error = order_request.reject(
            serializer.validated_data.get("reason", "")
        )
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DriverOrderRequestSerializer(order_request).data)


@extend_schema_view(
    list=extend_schema(summary="طلبات السائق", tags=["Driver - Orders"]),
    retrieve=extend_schema(summary="تفاصيل الطلب للسائق", tags=["Driver - Orders"]),
)
class DriverOrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != "driver":
            return Order.objects.none()
        return (
            Order.objects.filter(driver=user)
            .select_related("restaurant", "user")
            .prefetch_related("items")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return DriverOrderListSerializer
        return DriverOrderDetailSerializer

    @extend_schema(summary="الطلب الحالي", tags=["Driver - Orders"])
    @action(detail=False, methods=["get"])
    def current(self, request):
        order = (
            self.get_queryset()
            .filter(status__in=[OrderStatus.PREPARING, OrderStatus.PICKED])
            .first()
        )
        if not order:
            return Response(
                {"message": "لا يوجد طلب نشط حالياً"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(DriverOrderDetailSerializer(order).data)

    @extend_schema(summary="سجل الطلبات للسائق", tags=["Driver - Orders"])
    @action(detail=False, methods=["get"])
    def history(self, request):
        orders = self.get_queryset().filter(status=OrderStatus.DELIVERED)
        return Response(DriverOrderListSerializer(orders, many=True).data)

    @extend_schema(
        summary="عدد الطلبات المكتملة للسائق",
        tags=["Driver - Orders"],
        responses={200: {"type": "object", "properties": {"orders_count": {"type": "integer"}}}},
    )
    @action(detail=False, methods=["get"])
    def completed_count(self, request):
        count = self.get_queryset().filter(status=OrderStatus.DELIVERED).count()
        return Response({"orders_count": count})


@extend_schema(
    summary="تحديث حالة الطلب (سائق)",
    tags=["Driver - Orders"],
    request=DriverUpdateOrderStatusSerializer,
    responses={200: DriverOrderDetailSerializer},
)
class DriverUpdateOrderStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        if request.user.role != "driver":
            return Response(
                {"error": "هذه الخدمة للسائقين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        order = get_object_or_404(Order, id=order_id, driver=request.user)
        serializer = DriverUpdateOrderStatusSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)
        success, error = order.update_status(
            serializer.validated_data["status"], user=request.user
        )
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DriverOrderDetailSerializer(order).data)


@extend_schema(
    summary="تحديد سعر الطلب (سائق)",
    description="يستخدمها السائق بعد استلام الطلب من المحل لإدخال السعر الفعلي",
    tags=["Driver - Orders"],
    request=DriverSetOrderPriceSerializer,
    responses={200: DriverOrderDetailSerializer},
)
class DriverSetOrderPriceView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        if request.user.role != "driver":
            return Response(
                {"error": "هذه الخدمة للسائقين فقط"}, status=status.HTTP_403_FORBIDDEN
            )

        order = get_object_or_404(Order, id=order_id, driver=request.user)

        serializer = DriverSetOrderPriceSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)

        subtotal = serializer.validated_data["subtotal"]
        delivery_fee = order.delivery_fee

        # ── حساب restaurant_total مع العمولة — المنطق المصحح ──
        from decimal import Decimal

        restaurant = order.restaurant
        app_discount_pct = Decimal("0")

        if restaurant:
            app_discount_pct = restaurant.app_discount_percentage or Decimal("0")

            has_customer_discount = (
                restaurant.has_discount and restaurant.current_discount
            )

            if has_customer_discount:
                # الخصم للزبون — المطعم ياخد كامل subtotal
                restaurant_total = subtotal
            else:
                # عمولة للشركة — نخصم النسبة
                if app_discount_pct > 0:
                    restaurant_total = subtotal - (
                        subtotal * app_discount_pct / Decimal("100")
                    )
                else:
                    restaurant_total = subtotal
        else:
            # طلب يدوي بدون مطعم مسجل
            restaurant_total = subtotal

        order.subtotal = subtotal
        order.restaurant_total = restaurant_total
        order.app_discount_percentage = app_discount_pct
        order.total = subtotal + delivery_fee
        order.is_price_pending = False
        order.final_price_set_at = timezone.now()
        order.save(
            update_fields=[
                "subtotal",
                "restaurant_total",
                "app_discount_percentage",
                "total",
                "is_price_pending",
                "final_price_set_at",
                "updated_at",
            ]
        )

        # إشعار العميل بالسعر النهائي
        try:
            from notifications.services import NotificationService

            if order.user:
                NotificationService.create_notification(
                    user=order.user,
                    notification_type="order_price_updated",
                    title="تم تحديد سعر طلبك 💰",
                    body=f"سعر طلبك #{order.order_number} أصبح {order.total} ل.س",
                    title_en="Order Price Updated",
                    body_en=f"Your order #{order.order_number} total is now {order.total} SYP",
                    reference_type="order",
                    reference_id=order.id,
                    data={
                        "order_id": str(order.id),
                        "order_number": order.order_number,
                        "subtotal": str(order.subtotal),
                        "delivery_fee": str(order.delivery_fee),
                        "total": str(order.total),
                    },
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to notify user on price update: {e}"
            )

        return Response(DriverOrderDetailSerializer(order).data)


@extend_schema(
    summary="تحديث حالة الطلب (مطعم)",
    tags=["Restaurant - Orders"],
    request=UpdateOrderStatusSerializer,
    responses={200: OrderDetailSerializer},
)
class RestaurantUpdateOrderStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        serializer = UpdateOrderStatusSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)
        success, error = order.update_status(
            serializer.validated_data["status"],
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        if not success:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderDetailSerializer(order).data)


@extend_schema(
    summary="إرسال تقرير التسليم",
    tags=["Driver - Orders"],
    responses={201: OrderDeliveryReportSerializer},
)
class DriverSubmitDeliveryReportView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, order_id):
        if request.user.role != "driver":
            return Response(
                {"error": "هذه الخدمة للسائقين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        order = get_object_or_404(Order, id=order_id, driver=request.user)
        serializer = CreateDeliveryReportSerializer(
            data=request.data,
            context={"order": order, "driver": request.user},
        )
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(
            OrderDeliveryReportSerializer(report).data, status=status.HTTP_201_CREATED
        )
