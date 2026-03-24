"""
Admin Order Views - Order management for admins
"""

from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import Order
from ..serializers import (
    OrderDetailSerializer,
    AdminOrderListSerializer,
    AdminUpdateOrderStatusSerializer,
    CreateManualOrderSerializer,
    AdminOrderDetailSerializer,
)
from core.constants import OrderStatus


# ============================================
# ADMIN ORDER APIs
# ============================================


@extend_schema_view(
    list=extend_schema(
        summary="قائمة الطلبات للأدمن",
        description="عرض جميع الطلبات مع إمكانية الفلترة بالحالة والنوع والمطعم والسائق",
        tags=["Admin - Orders"],
    ),
    retrieve=extend_schema(summary="تفاصيل الطلب", tags=["Admin - Orders"]),
)
class AdminOrderViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return Order.objects.none()

        queryset = (
            Order.objects.all()
            .select_related("restaurant", "user", "driver", "driver__hero")
            .prefetch_related("items__order_item_addons", "status_history")
            .order_by("-created_at")
        )

        status_filter = self.request.query_params.get("status", OrderStatus.PLACED)
        if status_filter != "all":
            queryset = queryset.filter(status=status_filter)

        is_manual = self.request.query_params.get("is_manual")
        if is_manual is not None:
            queryset = queryset.filter(is_manual=is_manual.lower() == "true")

        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)

        driver_id = self.request.query_params.get("driver")
        if driver_id:
            if driver_id == "none":
                queryset = queryset.filter(driver__isnull=True)
            else:
                queryset = queryset.filter(driver_id=driver_id)

        payment_method = self.request.query_params.get("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        is_scheduled = self.request.query_params.get("is_scheduled")
        if is_scheduled is not None:
            queryset = queryset.filter(is_scheduled=is_scheduled.lower() == "true")

        chat_order_id = self.request.query_params.get("chat_order_id")
        if chat_order_id:
            queryset = queryset.filter(chat_order_id=chat_order_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(chat_order_id__icontains=search)
                | Q(contact_phone__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return AdminOrderListSerializer
        return AdminOrderDetailSerializer

    def list(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "هذه الخدمة للمشرفين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        queryset = self.get_queryset()

        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        serializer = self.get_serializer(queryset[start:end], many=True)
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )

    def retrieve(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"error": "Admins only"}, status=status.HTTP_403_FORBIDDEN)
        order = get_object_or_404(
            Order.objects.select_related(
                "restaurant", "user", "driver", "driver__hero", "coupon"
            ).prefetch_related(
                "items__product",
                "items__variation",
                "items__order_item_addons__addon",
                "status_history__changed_by",
            ),
            pk=pk,
        )
        return Response(AdminOrderDetailSerializer(order).data)

    @extend_schema(
        summary="تغيير حالة الطلب",
        description="تغيير الحالة إلى جاري التحضير أو إلغاء",
        tags=["Admin - Orders"],
        request=AdminUpdateOrderStatusSerializer,
        responses={200: OrderDetailSerializer},
    )
    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response(
                {"error": "هذه الخدمة للمشرفين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        order = get_object_or_404(Order, pk=pk)
        serializer = AdminUpdateOrderStatusSerializer(
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
    summary="إنشاء طلب يدوي",
    description="إنشاء طلب يدوي من قبل الأدمن (خارجي أو من الشات)",
    tags=["Admin - Orders"],
    request=CreateManualOrderSerializer,
    responses={201: OrderDetailSerializer},
)
class CreateManualOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "هذه الخدمة للمشرفين فقط"}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = CreateManualOrderSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED
        )
