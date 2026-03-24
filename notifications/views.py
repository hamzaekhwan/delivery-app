"""
Notifications Views
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import (
    Notification,
    DeviceToken,
    NotificationPreference,
    BroadcastNotification,
)
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    RegisterDeviceSerializer,
    UnregisterDeviceSerializer,
    DeviceTokenSerializer,
    NotificationPreferenceSerializer,
    BroadcastNotificationSerializer,
    UnreadCountSerializer,
)
from .services import NotificationService


from rest_framework.pagination import PageNumberPagination


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination  # ← أضف هذا

    @extend_schema(
        tags=["Notifications"],
        summary="List notifications",
        parameters=[
            OpenApiParameter(
                name="unread_only",
                type=bool,
                description="Filter unread notifications only",
            ),
            OpenApiParameter(
                name="type", type=str, description="Filter by notification type"
            ),
            OpenApiParameter(name="page", type=int, description="Page number"),
            OpenApiParameter(
                name="page_size", type=int, description="Results per page (max 50)"
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

        if self.request.query_params.get("unread_only") == "true":
            queryset = queryset.filter(is_read=False)

        notification_type = self.request.query_params.get("type")
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)

        return queryset  # ← احذف [:100] لأن الـ pagination يتكفل بالتحديد


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Get notification detail
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Get notification detail")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    """
    Mark a notification as read
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Mark notification as read")
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        return Response({"status": "success"})


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Mark all notifications as read")
    def post(self, request):
        count = NotificationService.mark_all_as_read(request.user)
        return Response({"status": "success", "count": count})


class UnreadCountView(APIView):
    """
    Get unread notifications count
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Get unread count",
        responses={200: UnreadCountSerializer},
    )
    def get(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({"count": count})


class RegisterDeviceView(APIView):
    """
    Register device for push notifications
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Register device token",
        request=RegisterDeviceSerializer,
        responses={201: DeviceTokenSerializer},
    )
    def post(self, request):
        serializer = RegisterDeviceSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        device = serializer.save()

        return Response(
            DeviceTokenSerializer(device).data, status=status.HTTP_201_CREATED
        )


class UnregisterDeviceView(APIView):
    """
    Unregister device from push notifications
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Unregister device token",
        request=UnregisterDeviceSerializer,
    )
    def post(self, request):
        serializer = UnregisterDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success = NotificationService.unregister_device(
            serializer.validated_data["token"]
        )

        if success:
            return Response({"status": "success"})
        return Response({"error": "Token not found"}, status=status.HTTP_404_NOT_FOUND)


class UserDevicesView(generics.ListAPIView):
    """
    List user's registered devices
    """

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="List registered devices")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user, is_active=True)


class NotificationPreferencesView(APIView):
    """
    Get and update notification preferences
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Get notification preferences",
        responses={200: NotificationPreferenceSerializer},
    )
    def get(self, request):
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)

    @extend_schema(
        tags=["Notifications"],
        summary="Update notification preferences",
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer},
    )
    def patch(self, request):
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            preferences, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DeleteNotificationView(APIView):
    """
    Delete a notification
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Delete notification")
    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClearNotificationsView(APIView):
    """
    Clear all notifications
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Notifications"], summary="Clear all notifications")
    def delete(self, request):
        count = Notification.objects.filter(user=request.user).delete()[0]
        return Response({"status": "success", "deleted": count})


# Admin Views


class BroadcastNotificationListView(generics.ListCreateAPIView):
    """
    List and create broadcast notifications (Admin only)
    """

    serializer_class = BroadcastNotificationSerializer
    permission_classes = [IsAdminUser]
    queryset = BroadcastNotification.objects.all()

    @extend_schema(
        tags=["Notifications - Admin"], summary="List broadcast notifications"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Notifications - Admin"], summary="Create broadcast notification"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SendBroadcastView(APIView):
    """
    Send a broadcast notification (Admin only)
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Notifications - Admin"], summary="Send broadcast notification"
    )
    def post(self, request, pk):
        broadcast = get_object_or_404(BroadcastNotification, pk=pk)

        if broadcast.is_sent:
            return Response(
                {"error": "Broadcast already sent"}, status=status.HTTP_400_BAD_REQUEST
            )

        results = NotificationService.send_broadcast(broadcast)

        return Response({"status": "success", "results": results})
