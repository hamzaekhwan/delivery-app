"""
Core Models - Base models and common functionality
"""

import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models.
    Provides:
    - UUID primary key (optional, use id as pk for FK relations)
    - Created at timestamp
    - Updated at timestamp
    - Soft delete capability
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SoftDeleteModel(BaseModel):
    """
    Abstract model with soft delete capability.
    Records are marked as deleted instead of being actually removed.
    """

    is_deleted = models.BooleanField(default=False, verbose_name="محذوف")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحذف")

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark the record as deleted"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class TimeStampedModel(models.Model):
    """
    Simple timestamp model without ordering
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Banner(BaseModel):
    """
    Banners for home page - Ramadan, Eid, promotions etc.
    """

    class BannerType(models.TextChoices):
        RAMADAN = "ramadan", "رمضان"
        EID = "eid", "عيد"
        PROMOTION = "promotion", "عرض"
        SEASONAL = "seasonal", "موسمي"
        GENERAL = "general", "عام"

    title = models.CharField(max_length=200, verbose_name="العنوان")
    title_en = models.CharField(
        max_length=200, blank=True, verbose_name="العنوان (إنجليزي)"
    )
    subtitle = models.CharField(
        max_length=300, blank=True, verbose_name="العنوان الفرعي"
    )
    subtitle_en = models.CharField(
        max_length=300, blank=True, verbose_name="العنوان الفرعي (إنجليزي)"
    )
    image = models.ImageField(upload_to="banners/", verbose_name="الصورة")
    banner_type = models.CharField(
        max_length=20,
        choices=BannerType.choices,
        default=BannerType.GENERAL,
        verbose_name="نوع البانر",
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="الرابط",
        help_text="رابط داخلي أو خارجي",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    start_date = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ البداية"
    )
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ النهاية")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "بانر"
        verbose_name_plural = "البانرات"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        """Check if banner is currently active based on dates"""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class AppConfiguration(models.Model):
    """
    Global app configuration - singleton pattern
    """

    # Delivery settings
    base_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=12000,
        verbose_name="رسوم التوصيل الأساسية",
        help_text="رسوم التوصيل للمسافة الأساسية (ل.س)",
    )
    free_distance_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3,
        verbose_name="المسافة الأساسية (كم)",
        help_text="المسافة المشمولة برسوم التوصيل الأساسية",
    )
    per_km_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=3000,
        verbose_name="رسوم الكيلومتر الإضافي",
        help_text="رسوم كل كيلومتر إضافي بعد المسافة الأساسية (ل.س)",
    )
    max_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="الحد الأقصى لرسوم التوصيل",
        help_text="0 يعني بدون حد أقصى",
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="حد التوصيل المجاني"
    )

    # Order settings
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الحد الأدنى للطلب"
    )
    preparation_lead_minutes = models.PositiveSmallIntegerField(
        "دقائق التحضير", default=0
    )

    # Driver settings
    driver_search_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
        verbose_name="نطاق البحث عن السائق (كم)",
    )
    driver_accept_timeout_seconds = models.PositiveIntegerField(
        default=60, verbose_name="مهلة قبول السائق (ثانية)"
    )
    min_online_drivers = models.PositiveIntegerField(
        default=0,
        verbose_name="الحد الأدنى للسائقين المتصلين",
        help_text="0 يعني بدون حد أدنى. إذا حاول سائق الخروج وعدد المتصلين سينقص عن هذا الحد، سيُمنع",
    )

    max_delivery_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15,
        verbose_name="أقصى نطاق توصيل (كم)",
        help_text="أقصى مسافة بين المستخدم والمطعم لعرضه في التطبيق",
    )

    # Home page settings
    recommended_weight_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.4,
        verbose_name="وزن التقييم في التوصيات",
    )
    recommended_weight_orders = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.3,
        verbose_name="وزن الطلبات في التوصيات",
    )
    recommended_weight_recent = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.3,
        verbose_name="وزن الطلبات الأخيرة في التوصيات",
    )
    recent_orders_days = models.PositiveIntegerField(
        default=30, verbose_name="عدد أيام الطلبات الأخيرة"
    )

    # Misc
    app_version = models.CharField(
        max_length=20, default="1.0.0", verbose_name="إصدار التطبيق"
    )
    maintenance_mode = models.BooleanField(default=False, verbose_name="وضع الصيانة")
    maintenance_message = models.TextField(blank=True, verbose_name="رسالة الصيانة")
    maintenance_message_en = models.TextField(
        blank=True, verbose_name="رسالة الصيانة (إنجليزي)"
    )

    class Meta:
        verbose_name = "إعدادات التطبيق"
        verbose_name_plural = "إعدادات التطبيق"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create the singleton configuration"""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return "إعدادات التطبيق"
