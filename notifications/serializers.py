"""
Notifications Serializers
"""

from rest_framework import serializers
from .models import (
    Notification,
    DeviceToken,
    NotificationPreference,
    BroadcastNotification,
)


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "title_en",
            "body",
            "body_en",
            "image_url",
            "reference_type",
            "reference_id",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing notifications"""

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title_en",
            "body_en",
            "title",
            "body",
            "is_read",
            "created_at",
        ]


class RegisterDeviceSerializer(serializers.Serializer):
    """Serializer for device registration"""

    token = serializers.CharField(max_length=255)
    device_type = serializers.ChoiceField(choices=["android", "ios", "web"])
    device_name = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    language = serializers.CharField(max_length=5, required=False, default="ar")

    def create(self, validated_data):
        from .services import NotificationService

        user = self.context["request"].user
        return NotificationService.register_device(
            user=user,
            token=validated_data["token"],
            device_type=validated_data["device_type"],
            device_name=validated_data.get("device_name"),
            language=validated_data.get("language", "ar"),
        )


class UnregisterDeviceSerializer(serializers.Serializer):
    """Serializer for device unregistration"""

    token = serializers.CharField(max_length=255)


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for device tokens"""

    class Meta:
        model = DeviceToken
        fields = ["id", "device_type", "device_name", "is_active", "last_used_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""

    class Meta:
        model = NotificationPreference
        fields = [
            "push_enabled",
            "email_enabled",
            "sms_enabled",
            "order_updates",
            "promotional",
            "new_restaurants",
            "review_reminders",
            "driver_updates",
            "quiet_hours_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
        ]

    def validate(self, data):
        # Validate quiet hours
        if data.get("quiet_hours_enabled"):
            if not data.get("quiet_hours_start") or not data.get("quiet_hours_end"):
                raise serializers.ValidationError(
                    {
                        "quiet_hours": "Start and end times are required when quiet hours are enabled."
                    }
                )
        return data


class BroadcastNotificationSerializer(serializers.ModelSerializer):
    """Serializer for broadcast notifications (admin)"""

    class Meta:
        model = BroadcastNotification
        fields = [
            "id",
            "title",
            "title_en",
            "body",
            "body_en",
            "image_url",
            "target_audience",
            "target_governorate",
            "action_type",
            "action_data",
            "scheduled_at",
            "is_sent",
            "sent_at",
            "total_recipients",
            "successful_sends",
            "failed_sends",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "is_sent",
            "sent_at",
            "total_recipients",
            "successful_sends",
            "failed_sends",
            "created_at",
        ]

    def validate(self, data):
        if data.get("target_audience") == "governorate" and not data.get(
            "target_governorate"
        ):
            raise serializers.ValidationError(
                {
                    "target_governorate": "Governorate is required for governorate targeting."
                }
            )
        return data


class UnreadCountSerializer(serializers.Serializer):
    """Serializer for unread count response"""

    count = serializers.IntegerField()
