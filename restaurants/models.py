"""
Restaurant Models - Restaurant, Categories, and related models
"""

from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from core.models import BaseModel
from core.constants import RestaurantType
from core.utils import is_within_working_hours


class RestaurantCategory(BaseModel):
    """
    Main categories for restaurants (e.g., Fast Food, Pizza, Shawarma)
    """

    name = models.CharField(max_length=100, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(unique=True, verbose_name="المعرف")
    icon = models.ImageField(
        upload_to="restaurant_categories/",
        blank=True,
        null=True,
        verbose_name="الأيقونة",
    )
    image = models.ImageField(
        upload_to="restaurant_categories/", blank=True, null=True, verbose_name="الصورة"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        verbose_name = "تصنيف مطعم"
        verbose_name_plural = "تصنيفات المطاعم"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name_en or self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while (
                RestaurantCategory.objects.filter(slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Restaurant(BaseModel):
    """
    Restaurant/Store model - supports multiple types (Food, Grocery, Pharmacy)
    """

    name = models.CharField(max_length=200, verbose_name="اسم المطعم")
    name_en = models.CharField(
        max_length=200, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(unique=True, verbose_name="المعرف")
    description = models.TextField(blank=True, verbose_name="الوصف")
    description_en = models.TextField(blank=True, verbose_name="الوصف (إنجليزي)")

    # Images
    logo = models.ImageField(
        upload_to="restaurants/logos/",
        verbose_name="الشعار",
        blank=True,
        null=True,
    )
    cover_image = models.ImageField(
        upload_to="restaurants/covers/",
        blank=True,
        null=True,
        verbose_name="صورة الغلاف",
    )

    # Type and Category
    restaurant_type = models.CharField(
        max_length=20,
        choices=RestaurantType.choices,
        default=RestaurantType.FOOD,
        verbose_name="نوع المتجر",
    )
    categories = models.ManyToManyField(
        RestaurantCategory,
        blank=True,
        related_name="restaurants",
        verbose_name="التصنيفات",
    )

    # Location
    address = models.CharField(max_length=500, verbose_name="العنوان")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط العرض"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط الطول"
    )

    # Contact
    phone = models.CharField(max_length=20, blank=True, verbose_name="رقم الهاتف")

    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    is_open = models.BooleanField(default=True, verbose_name="مفتوح")

    # Working Hours (24h format: "HH:MM")
    opening_time = models.CharField(
        max_length=5,
        default="08:00",
        verbose_name="وقت الفتح",
        help_text="صيغة 24 ساعة (مثال: 08:00)",
    )
    closing_time = models.CharField(
        max_length=5,
        default="23:00",
        verbose_name="وقت الإغلاق",
        help_text="صيغة 24 ساعة (مثال: 23:00)",
    )

    # Order Settings
    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الحد الأدنى للطلب"
    )
    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="رسوم التوصيل"
    )
    delivery_time_estimate = models.CharField(
        max_length=50,
        default="30-45",
        verbose_name="وقت التوصيل المقدر",
        help_text="بالدقائق (مثال: 30-45)",
    )

    # App Commission (discount from restaurant)
    app_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="نسبة تخفيض التطبيق",
        help_text="النسبة المئوية التي يأخذها التطبيق كتخفيض من المطعم (مثال: 10 تعني 10%)",
    )

    # Discount Settings
    has_discount = models.BooleanField(default=False, verbose_name="يوجد خصم")
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="نسبة الخصم"
    )
    discount_start_time = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="وقت بداية الخصم",
        help_text="صيغة 24 ساعة",
    )
    discount_end_time = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="وقت نهاية الخصم",
        help_text="صيغة 24 ساعة",
    )

    # Statistics (cached for performance)
    total_orders = models.PositiveIntegerField(default=0, verbose_name="إجمالي الطلبات")
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, verbose_name="متوسط التقييم"
    )
    total_reviews = models.PositiveIntegerField(default=0, verbose_name="عدد التقييمات")

    # Featured
    is_featured = models.BooleanField(default=False, verbose_name="مميز")

    class Meta:
        verbose_name = "مطعم"
        verbose_name_plural = "المطاعم"
        ordering = ["-is_featured", "-average_rating", "name"]
        indexes = [
            models.Index(fields=["is_active", "is_open"]),
            models.Index(fields=["restaurant_type"]),
            models.Index(fields=["average_rating"]),
            models.Index(fields=["total_orders"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name_en or self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_currently_open(self):
        """Check if restaurant is currently open based on working hours"""
        if not self.is_open:
            return False
        return is_within_working_hours(self.opening_time, self.closing_time)

    @property
    def current_discount(self):
        """Get current discount if applicable"""
        if not self.has_discount:
            return None

        if self.discount_start_time and self.discount_end_time:
            if is_within_working_hours(
                self.discount_start_time, self.discount_end_time
            ):
                return self.discount_percentage
        elif self.has_discount:
            return self.discount_percentage

        return None

    def update_statistics(self):
        """Update cached statistics from orders and reviews"""
        from orders.models import Order
        from reviews.models import RestaurantReview
        from django.db.models import Avg, Count
        from core.constants import OrderStatus

        # Update orders count
        self.total_orders = Order.objects.filter(
            restaurant=self, status__in=[OrderStatus.COMPLETED, OrderStatus.DELIVERED]
        ).count()

        # Update reviews statistics
        stats = RestaurantReview.objects.filter(restaurant=self).aggregate(
            avg_rating=Avg("rating"), count=Count("id")
        )

        self.average_rating = stats["avg_rating"] or 0
        self.total_reviews = stats["count"] or 0

        self.save(update_fields=["total_orders", "average_rating", "total_reviews"])


class RestaurantWorkingHours(BaseModel):
    """
    Detailed working hours per day of week
    """

    class DayOfWeek(models.IntegerChoices):
        SATURDAY = 0, "السبت"
        SUNDAY = 1, "الأحد"
        MONDAY = 2, "الاثنين"
        TUESDAY = 3, "الثلاثاء"
        WEDNESDAY = 4, "الأربعاء"
        THURSDAY = 5, "الخميس"
        FRIDAY = 6, "الجمعة"

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="working_hours",
        verbose_name="المطعم",
    )
    day = models.IntegerField(choices=DayOfWeek.choices, verbose_name="اليوم")
    opening_time = models.CharField(max_length=5, verbose_name="وقت الفتح")
    closing_time = models.CharField(max_length=5, verbose_name="وقت الإغلاق")
    is_closed = models.BooleanField(default=False, verbose_name="مغلق")

    class Meta:
        verbose_name = "ساعات العمل"
        verbose_name_plural = "ساعات العمل"
        unique_together = ["restaurant", "day"]
        ordering = ["day"]

    def __str__(self):
        return f"{self.restaurant.name} - {self.get_day_display()}"
