"""
Coupon Views - API endpoints for coupons
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from decimal import Decimal

from .models import Coupon
from .serializers import (
    CouponSerializer,
    CouponValidationSerializer,
    CouponValidationResponseSerializer,
)


class ValidateCouponView(APIView):
    """
    Validate a coupon code
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="التحقق من الكوبون",
        description="التحقق من صلاحية كوبون معين",
        tags=["Coupons"],
        request=CouponValidationSerializer,
        responses={200: CouponValidationResponseSerializer},
    )
    def post(self, request):
        serializer = CouponValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"].upper()
        restaurant_id = serializer.validated_data.get("restaurant_id")
        order_amount = serializer.validated_data.get("order_amount", Decimal("0"))

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response({"valid": False, "message": "كود الكوبون غير موجود"})

        # Get restaurant if provided
        restaurant = None
        if restaurant_id:
            from restaurants.models import Restaurant

            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                pass

        # Check if coupon can be used
        can_use, error_message = coupon.can_be_used_by(request.user, restaurant)

        if not can_use:
            return Response({"valid": False, "message": error_message})

        # Check minimum order amount
        if order_amount < coupon.minimum_order_amount:
            return Response(
                {
                    "valid": False,
                    "message": f"الحد الأدنى للطلب هو {coupon.minimum_order_amount}",
                }
            )

        # Calculate discount
        discount_amount = coupon.calculate_discount(order_amount)

        return Response(
            {
                "valid": True,
                "coupon": CouponSerializer(coupon).data,
                "discount_amount": discount_amount,
                "message": "الكوبون صالح",
            }
        )


class AvailableCouponsView(generics.ListAPIView):
    """
    List available coupons for the user
    """

    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="الكوبونات المتاحة",
        description="الحصول على قائمة الكوبونات المتاحة للمستخدم",
        tags=["Coupons"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from django.utils import timezone

        now = timezone.now()

        # Get all active coupons
        coupons = Coupon.objects.filter(
            is_active=True, start_date__lte=now, end_date__gte=now
        )

        # Filter out fully used coupons
        coupons = coupons.exclude(
            usage_limit__isnull=False, times_used__gte=models.F("usage_limit")
        )

        # Exclude coupons user has already used up
        from .models import CouponUsage
        from django.db.models import Count

        user_usages = (
            CouponUsage.objects.filter(user=self.request.user)
            .values("coupon")
            .annotate(count=Count("id"))
        )

        used_coupon_ids = [
            u["coupon"]
            for u in user_usages
            if Coupon.objects.filter(
                id=u["coupon"], usage_limit_per_user__lte=u["count"]
            ).exists()
        ]

        return coupons.exclude(id__in=used_coupon_ids)


# Import models for queryset
from django.db import models
