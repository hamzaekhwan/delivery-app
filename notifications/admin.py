"""
Notifications Admin Configuration
"""

from django.contrib import admin
from .models import (
    DeviceToken,
    Notification,
    NotificationPreference,
    BroadcastNotification,
)
from .services import NotificationService


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "device_type",
        "device_name",
        "is_active",
        "last_used_at",
    ]
    list_filter = ["device_type", "is_active"]
    search_fields = ["user__phone_number", "user__full_name", "token", "device_name"]
    readonly_fields = ["last_used_at", "created_at"]
    list_per_page = 50


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "notification_type",
        "title_truncated",
        "is_read",
        "push_sent",
        "created_at",
    ]
    list_filter = ["notification_type", "is_read", "push_sent", "created_at"]
    search_fields = ["user__phone_number", "user__full_name", "title", "body"]
    readonly_fields = [
        "user",
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
        "push_sent",
        "push_sent_at",
        "created_at",
    ]
    list_per_page = 50
    date_hierarchy = "created_at"

    def title_truncated(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title

    title_truncated.short_description = "العنوان"

    def has_add_permission(self, request):
        return False

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "push_enabled",
        "email_enabled",
        "sms_enabled",
        "quiet_hours_enabled",
    ]
    list_filter = [
        "push_enabled",
        "email_enabled",
        "sms_enabled",
        "quiet_hours_enabled",
    ]
    search_fields = ["user__phone_number", "user__full_name"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("المستخدم", {"fields": ("user",)}),
        (
            "الإعدادات العامة",
            {"fields": ("push_enabled", "email_enabled", "sms_enabled")},
        ),
        (
            "أنواع الإشعارات",
            {
                "fields": (
                    "order_updates",
                    "promotional",
                    "new_restaurants",
                    "review_reminders",
                    "driver_updates",
                )
            },
        ),
        (
            "ساعات الهدوء",
            {
                "fields": (
                    "quiet_hours_enabled",
                    "quiet_hours_start",
                    "quiet_hours_end",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(BroadcastNotification)
class BroadcastNotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "target_audience",
        "is_sent",
        "total_recipients",
        "successful_sends",
        "sent_at",
        "created_at",
    ]
    list_filter = ["target_audience", "is_sent", "created_at"]
    search_fields = ["title", "body"]
    readonly_fields = [
        "is_sent",
        "sent_at",
        "total_recipients",
        "successful_sends",
        "failed_sends",
        "created_by",
        "created_at",
    ]
    list_per_page = 25
    date_hierarchy = "created_at"

    actions = ["send_broadcast"]

    fieldsets = (
        ("المحتوى", {"fields": ("title", "title_en", "body", "body_en", "image_url")}),
        ("الاستهداف", {"fields": ("target_audience", "target_governorate")}),
        (
            "الإجراء",
            {"fields": ("action_type", "action_data"), "classes": ("collapse",)},
        ),
        ("الجدولة", {"fields": ("scheduled_at",), "classes": ("collapse",)}),
        (
            "الحالة",
            {
                "fields": (
                    "is_sent",
                    "sent_at",
                    "total_recipients",
                    "successful_sends",
                    "failed_sends",
                )
            },
        ),
        (
            "معلومات النظام",
            {"fields": ("created_by", "created_at"), "classes": ("collapse",)},
        ),
    )

    @admin.action(description="إرسال الإشعارات المحددة")
    def send_broadcast(self, request, queryset):
        sent = 0
        for broadcast in queryset.filter(is_sent=False):
            NotificationService.send_broadcast(broadcast)
            sent += 1
        self.message_user(request, f"تم إرسال {sent} إشعار جماعي")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
