"""
Authentication Views - SignUp, Login, OTP, Password
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
)

from ..models import User, OTP
from ..serializers import (
    SignUpSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    LoginSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    LogoutSerializer,
)
from ..services import send_otp_with_fallback

logger = logging.getLogger(__name__)

DEBUG_MODE = getattr(settings, "DEBUG", True)


def get_tokens_for_user(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def send_otp_message(phone_number, otp_code, otp_type):
    """Send OTP via WhatsApp first, fallback to SMS"""
    return send_otp_with_fallback(phone_number, otp_code, otp_type)


# =============================================================================
# AUTHENTICATION VIEWS (unchanged)
# =============================================================================


@extend_schema(tags=["Authentication"])
class SignUpView(APIView):
    """Register a new user account"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register new account",
        description="Create a new user account and send OTP for verification",
        request=SignUpSerializer,
        responses={
            201: OpenApiResponse(description="Account created successfully"),
            400: OpenApiResponse(description="Invalid data"),
        },
    )
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            otp = OTP.create_otp(user, OTP.OTPType.SIGNUP)
            send_otp_message(user.phone_number, otp.code, "signup")

            response_data = {
                "success": True,
                "message": "Account created successfully. Please verify OTP",
                "phone_number": user.phone_number,
            }

            # if DEBUG_MODE:
            #     response_data["debug_otp"] = otp.code

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class VerifyOTPView(APIView):
    """Verify OTP code"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify OTP",
        description="Verify OTP code to activate account or reset password",
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(description="Verification successful"),
            400: OpenApiResponse(description="Invalid or expired OTP"),
        },
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            otp = serializer.validated_data["otp"]
            otp_type = serializer.validated_data["otp_type"]

            otp.is_used = True
            otp.save()

            if otp_type == OTP.OTPType.SIGNUP:
                user.is_active = True
                user.save()
                tokens = get_tokens_for_user(user)

                return Response(
                    {
                        "success": True,
                        "message": "Account activated successfully",
                        "user": UserSerializer(user).data,
                        "tokens": tokens,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": True,
                        "message": "OTP verified. You can now reset your password",
                        "can_reset_password": True,
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class ResendOTPView(APIView):
    """Resend OTP code"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Resend OTP",
        description="Resend a new OTP code to the phone number",
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent successfully"),
            400: OpenApiResponse(description="User not found"),
        },
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)

        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            otp_type = serializer.validated_data["otp_type"]

            user = User.objects.get(phone_number=phone_number)
            otp = OTP.create_otp(user, otp_type)
            send_otp_message(user.phone_number, otp.code, otp_type)

            response_data = {"success": True, "message": "New OTP code sent"}

            if DEBUG_MODE:
                response_data["debug_otp"] = otp.code

            return Response(response_data, status=status.HTTP_200_OK)

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    """User login"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login",
        description="Login with phone number and password. Works for users and drivers",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            400: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_tokens_for_user(user)

            return Response(
                {
                    "success": True,
                    "message": "Login successful",
                    "user": UserSerializer(user).data,
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class ForgotPasswordView(APIView):
    """Request password reset"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Forgot Password",
        description="Request OTP to reset password",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent successfully"),
            400: OpenApiResponse(description="User not found"),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            user = User.objects.get(phone_number=phone_number, is_active=True)
            otp = OTP.create_otp(user, OTP.OTPType.FORGOT_PASSWORD)
            send_otp_message(user.phone_number, otp.code, "forgot_password")

            response_data = {
                "success": True,
                "message": "OTP sent to your phone number",
            }

            if DEBUG_MODE:
                response_data["debug_otp"] = otp.code

            return Response(response_data, status=status.HTTP_200_OK)

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class ResetPasswordView(APIView):
    """Reset password with OTP"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Reset Password",
        description="Reset password using OTP code",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successful"),
            400: OpenApiResponse(description="Invalid OTP or data"),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            otp = serializer.validated_data["otp"]

            user.set_password(serializer.validated_data["new_password"])
            user.save()

            otp.is_used = True
            otp.save()

            return Response(
                {
                    "success": True,
                    "message": "Password reset successful. Please login with new password",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    """Logout user"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout",
        description="Logout and invalidate refresh token",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
        },
    )
    def post(self, request):
        # If driver or admin, go offline first
        if request.user.is_online:
            request.user.go_offline()

        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        return Response(
            {"success": True, "message": "Logged out successfully"},
            status=status.HTTP_200_OK,
        )
