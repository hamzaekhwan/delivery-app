"""
Profile Views - Profile, Language, ChangePassword, DeleteAccount
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
)

from ..models import User, Hero
from ..serializers import (
    UserSerializer,
    ChangePasswordSerializer,
    DeleteAccountSerializer,
    LanguageSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Profile"])
class ProfileView(APIView):
    """Get and update user profile"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Profile",
        description="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(
            {"success": True, "user": UserSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Update Profile",
        description="Update user profile information",
        request=UserSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "user": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Profile"])
class ChangePasswordView(APIView):
    """Change password"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change Password",
        description="Change password while logged in",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Invalid old password"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.save()

            return Response(
                {"success": True, "message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LanguageView(APIView):
    """
    GET  /api/language/   → جلب اللغة الحالية للمستخدم
    PATCH /api/language/  → تغيير اللغة (ar أو en)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """جلب اللغة الحالية"""
        serializer = LanguageSerializer(request.user)
        return Response(
            {
                "success": True,
                "data": serializer.data,
                "available_languages": [
                    {"code": "ar", "name": "العربية"},
                    {"code": "en", "name": "English"},
                ],
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        """تغيير اللغة"""
        serializer = LanguageSerializer(
            request.user,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": (
                        "تم تغيير اللغة بنجاح"
                        if request.user.language == "ar"
                        else "Language updated successfully"
                    ),
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ============================================
# DELETE ACCOUNT
# ============================================


@extend_schema(tags=["Accounts"])
class DeleteAccountView(APIView):
    """
    حذف (تعطيل) حساب المستخدم - Soft Delete
    يعطّل الحساب بدل حذفه للحفاظ على سجل الطلبات والتقييمات.
    مطلوب من Apple App Store (Guideline 5.1.1).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="حذف الحساب",
        description="تعطيل حساب المستخدم نهائياً. يتطلب تأكيد كلمة المرور.",
        request=DeleteAccountSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = DeleteAccountSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        # إذا أونلاين، سجّل خروجه
        if user.is_online:
            user.go_offline()

        # إلغاء الطلبات النشطة
        from orders.models import Order
        from core.constants import OrderStatus

        active_orders = Order.objects.filter(
            user=user,
            status__in=[OrderStatus.DRAFT, OrderStatus.PLACED],
        )
        for order in active_orders:
            order.update_status(
                OrderStatus.CANCELLED,
                user=user,
                reason="تم حذف حساب المستخدم",
            )

        # تعطيل tokens الأجهزة
        from notifications.models import DeviceToken

        DeviceToken.objects.filter(user=user).update(is_active=False)

        # حذف السلات
        from cart.models import Cart

        Cart.objects.filter(user=user).delete()

        # تسجيل السبب قبل الحذف
        reason = serializer.validated_data.get("reason", "")
        if reason:
            logger.info(f"Account permanently deleted: user={user.id}, reason={reason}")
        else:
            logger.info(f"Account permanently deleted: user={user.id}")

        # إلغاء JWT tokens
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        # الحذف النهائي للحساب
        user.delete()

        return Response(
            {
                "success": True,
                "message": "تم حذف حسابك بشكل نهائي.",
                "message_en": "Your account has been permanently deleted.",
            },
            status=status.HTTP_200_OK,
        )
