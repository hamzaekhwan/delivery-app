"""
Cart Views - Coupon and checkout operations
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from ..models import Cart
from ..serializers import CartSerializer, ApplyCouponSerializer
from .cart_operations import CartCleanupMixin


# ═══════════════════════════════════════════════════════════
#                    Coupon Operations
# ═══════════════════════════════════════════════════════════
class ApplyCouponView(CartCleanupMixin, APIView):
    """
    Apply coupon to cart
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="تطبيق كوبون",
        description="تطبيق كوبون خصم على السلة",
        tags=["Cart"],
        request=ApplyCouponSerializer,
        responses={200: CartSerializer},
    )
    def post(self, request, cart_id):
        self.perform_cleanup(request.user)

        serializer = ApplyCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cart = Cart.objects.for_user(request.user).get(id=cart_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND
            )

        code = serializer.validated_data["code"].upper()

        from coupons.models import Coupon

        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response(
                {"error": "كود الكوبون غير صحيح"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart.apply_coupon(coupon)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data)

    @extend_schema(
        summary="إزالة الكوبون",
        description="إزالة الكوبون من السلة",
        tags=["Cart"],
        responses={200: CartSerializer},
    )
    def delete(self, request, cart_id):
        self.perform_cleanup(request.user)

        try:
            cart = Cart.objects.for_user(request.user).get(id=cart_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة"}, status=status.HTTP_404_NOT_FOUND
            )

        cart.remove_coupon()
        cart.refresh_from_db()
        return Response(CartSerializer(cart).data)


# ═══════════════════════════════════════════════════════════
#                    Validate Cart
# ═══════════════════════════════════════════════════════════
class ValidateCartView(CartCleanupMixin, APIView):
    """
    Validate cart for checkout
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="التحقق من السلة",
        description="التحقق من صلاحية السلة للدفع",
        tags=["Cart"],
        parameters=[
            OpenApiParameter(
                name="cart_id", description="معرف السلة", required=True, type=int
            ),
        ],
    )
    def get(self, request):
        self.perform_cleanup(request.user)

        cart_id = request.query_params.get("cart_id")

        if not cart_id:
            return Response(
                {"error": "cart_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart = Cart.objects.for_user(request.user).get(id=cart_id)
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة أو منتهية الصلاحية"},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_valid, errors = cart.validate_for_checkout()

        return Response(
            {"valid": is_valid, "errors": errors, "cart": CartSerializer(cart).data}
        )


# ═══════════════════════════════════════════════════════════
#                    Select Cart for Checkout
# ═══════════════════════════════════════════════════════════
class SelectCartView(CartCleanupMixin, APIView):
    """
    Select a cart for checkout (returns cart details with validation)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="اختيار سلة للدفع",
        description="اختيار سلة معينة للمتابعة للدفع",
        tags=["Cart"],
    )
    def post(self, request, cart_id):
        self.perform_cleanup(request.user)

        try:
            cart = (
                Cart.objects.for_user(request.user)
                .select_related("restaurant", "coupon")
                .prefetch_related(
                    "items__product",
                    "items__variation",
                    "items__cart_item_addons__addon",
                )
                .get(id=cart_id)
            )
        except Cart.DoesNotExist:
            return Response(
                {"error": "السلة غير موجودة أو منتهية الصلاحية"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate cart
        is_valid, errors = cart.validate_for_checkout()

        # Refresh expiry since user is actively using this cart
        cart.refresh_expiry()

        return Response(
            {
                "cart": CartSerializer(cart).data,
                "valid_for_checkout": is_valid,
                "validation_errors": errors,
                "price_breakdown": cart.get_price_breakdown(),
            }
        )
