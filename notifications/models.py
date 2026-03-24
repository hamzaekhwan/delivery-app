"""
Notifications Models - Push Notifications and In-App Notifications
"""

from django.db import models
from django.conf import settings
from core.models import BaseModel
from core.constants import NotificationType


class DeviceToken(BaseModel):
    """
    Store FCM device tokens for push notifications
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
        verbose_name="المستخدم",
    )
    token = models.CharField(max_length=255, unique=True, verbose_name="التوكن")
    device_type = models.CharField(
        max_length=20,
        choices=[
            ("android", "أندرويد"),
            ("ios", "iOS"),
            ("web", "ويب"),
        ],
        verbose_name="نوع الجهاز",
    )
    device_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="اسم الجهاز"
    )
    language = models.CharField(
        max_length=5,
        default="ar",
        verbose_name="لغة الجهاز",
        help_text="لغة الإشعارات (ar/en)",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    last_used_at = models.DateTimeField(auto_now=True, verbose_name="آخر استخدام")

    class Meta:
        verbose_name = "توكن جهاز"
        verbose_name_plural = "توكنات الأجهزة"
        ordering = ["-last_used_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.device_type} ({self.token[:20]}...)"


class Notification(BaseModel):
    """
    In-app notifications for users
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="المستخدم",
    )

    # Notification type
    notification_type = models.CharField(
        max_length=50,
        choices=[(t.value, t.value) for t in NotificationType],
        default=NotificationType.GENERAL.value,
        verbose_name="نوع الإشعار",
    )

    # Content
    title = models.CharField(max_length=255, verbose_name="العنوان")
    title_en = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="العنوان (إنجليزي)"
    )
    body = models.TextField(verbose_name="المحتوى")
    body_en = models.TextField(blank=True, null=True, verbose_name="المحتوى (إنجليزي)")

    # Optional image
    image_url = models.URLField(blank=True, null=True, verbose_name="رابط الصورة")

    # Reference data (for navigation)
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="نوع العنصر المرتبط (طلب، مطعم، إلخ)",
        verbose_name="نوع المرجع",
    )
    reference_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="معرّف العنصر المرتبط",
        verbose_name="معرّف المرجع",
    )

    # Extra data as JSON
    data = models.JSONField(default=dict, blank=True, verbose_name="بيانات إضافية")

    # Status
    is_read = models.BooleanField(default=False, verbose_name="مقروء")
    read_at = models.DateTimeField(blank=True, null=True, verbose_name="وقت القراءة")

    # Push notification status
    push_sent = models.BooleanField(default=False, verbose_name="تم الإرسال")
    push_sent_at = models.DateTimeField(
        blank=True, null=True, verbose_name="وقت الإرسال"
    )

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
            models.Index(fields=["notification_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.user}"

    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])


class NotificationPreference(BaseModel):
    """
    User notification preferences
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name="المستخدم",
    )

    # General settings
    push_enabled = models.BooleanField(default=True, verbose_name="تفعيل الإشعارات")
    email_enabled = models.BooleanField(default=False, verbose_name="تفعيل البريد")
    sms_enabled = models.BooleanField(default=False, verbose_name="تفعيل الرسائل")

    # Specific notification types
    order_updates = models.BooleanField(default=True, verbose_name="تحديثات الطلبات")
    promotional = models.BooleanField(default=True, verbose_name="العروض الترويجية")
    new_restaurants = models.BooleanField(default=True, verbose_name="مطاعم جديدة")
    review_reminders = models.BooleanField(default=True, verbose_name="تذكير بالتقييم")
    driver_updates = models.BooleanField(default=True, verbose_name="تحديثات السائق")

    # Quiet hours
    quiet_hours_enabled = models.BooleanField(
        default=False, verbose_name="تفعيل ساعات الهدوء"
    )
    quiet_hours_start = models.TimeField(
        blank=True,
        null=True,
        verbose_name="بداية ساعات الهدوء",
    )
    quiet_hours_end = models.TimeField(
        blank=True,
        null=True,
        verbose_name="نهاية ساعات الهدوء",
    )

    class Meta:
        verbose_name = "تفضيل إشعارات"
        verbose_name_plural = "تفضيلات الإشعارات"

    def __str__(self):
        return f"تفضيلات الإشعارات - {self.user}"

    def can_send_notification(self, notification_type):
        """Check if a specific notification type is enabled"""
        if not self.push_enabled:
            return False

        # Check quiet hours
        if self.quiet_hours_enabled and self.quiet_hours_start and self.quiet_hours_end:
            from django.utils import timezone

            current_time = timezone.localtime().time()

            # Handle overnight quiet hours
            if self.quiet_hours_start <= self.quiet_hours_end:
                if self.quiet_hours_start <= current_time <= self.quiet_hours_end:
                    return False
            else:
                if (
                    current_time >= self.quiet_hours_start
                    or current_time <= self.quiet_hours_end
                ):
                    return False

        # Check specific notification type
        type_mapping = {
            NotificationType.ORDER_PLACED.value: self.order_updates,
            NotificationType.ORDER_PREPARING.value: self.order_updates,
            NotificationType.ORDER_PICKED.value: self.order_updates,
            NotificationType.ORDER_DELIVERED.value: self.order_updates,
            NotificationType.ORDER_CANCELLED.value: self.order_updates,
            NotificationType.PROMOTION.value: self.promotional,
            NotificationType.NEW_ORDER_FOR_DRIVER.value: self.driver_updates,
            NotificationType.DRIVER_ASSIGNED.value: self.order_updates,
        }

        return type_mapping.get(notification_type, True)


class BroadcastNotification(BaseModel):
    """
    Broadcast notifications sent to multiple users
    """

    title = models.CharField(max_length=255, verbose_name="العنوان")
    title_en = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="العنوان (إنجليزي)"
    )
    body = models.TextField(verbose_name="المحتوى")
    body_en = models.TextField(blank=True, null=True, verbose_name="المحتوى (إنجليزي)")
    image_url = models.URLField(blank=True, null=True, verbose_name="رابط الصورة")

    # Targeting
    target_audience = models.CharField(
        max_length=50,
        choices=[
            ("all", "الكل"),
            ("users", "الزبائن فقط"),
            ("drivers", "السائقين فقط"),
            ("governorate", "محافظة محددة"),
        ],
        default="all",
        verbose_name="الجمهور المستهدف",
    )
    target_governorate = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="مطلوب إذا كان الجمهور 'محافظة محددة'",
        verbose_name="المحافظة المستهدفة",
    )

    # Action data
    action_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("open_app", "فتح التطبيق"),
            ("open_restaurant", "فتح مطعم"),
            ("open_category", "فتح تصنيف"),
            ("open_url", "فتح رابط"),
        ],
        verbose_name="نوع الإجراء",
    )
    action_data = models.JSONField(
        default=dict, blank=True, verbose_name="بيانات الإجراء"
    )

    # Scheduling
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="جدولة للإرسال لاحقاً",
        verbose_name="موعد الإرسال المجدول",
    )
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name="وقت الإرسال")
    is_sent = models.BooleanField(default=False, verbose_name="تم الإرسال")

    # Stats
    total_recipients = models.PositiveIntegerField(
        default=0, verbose_name="إجمالي المستلمين"
    )
    successful_sends = models.PositiveIntegerField(default=0, verbose_name="إرسال ناجح")
    failed_sends = models.PositiveIntegerField(default=0, verbose_name="إرسال فاشل")

    # Created by admin
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_broadcasts",
        verbose_name="أُنشئ بواسطة",
    )

    class Meta:
        verbose_name = "إشعار جماعي"
        verbose_name_plural = "الإشعارات الجماعية"
        ordering = ["-created_at"]

    def __str__(self):
        return f"إشعار جماعي: {self.title}"
