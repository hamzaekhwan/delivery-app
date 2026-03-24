"""
Coupons Models - Coupon system for discounts
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel
from core.constants import DiscountType, CouponStatus
from django.db.models import F


class Coupon(BaseModel):
    """
    Coupon model for order discounts
    """

    code = models.CharField(max_length=50, unique=True, verbose_name="كود الكوبون")
    description = models.TextField(blank=True, verbose_name="الوصف")
    description_en = models.TextField(blank=True, verbose_name="الوصف (إنجليزي)")

    # Discount settings
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        verbose_name="نوع الخصم",
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="قيمة الخصم"
    )
    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="الحد الأقصى للخصم",
        help_text="للخصم بالنسبة المئوية",
    )

    # Validity
    start_date = models.DateTimeField(verbose_name="تاريخ البداية")
    end_date = models.DateTimeField(verbose_name="تاريخ النهاية")

    # Usage limits
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="حد الاستخدام الكلي"
    )
    usage_limit_per_user = models.PositiveIntegerField(
        default=1, verbose_name="حد الاستخدام لكل مستخدم"
    )
    times_used = models.PositiveIntegerField(
        default=0, verbose_name="عدد مرات الاستخدام"
    )

    # Requirements
    minimum_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الحد الأدنى للطلب"
    )

    # Restrictions
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="coupons",
        verbose_name="المطعم",
        help_text="اتركه فارغاً لتطبيقه على جميع المطاعم",
    )
    first_order_only = models.BooleanField(
        default=False, verbose_name="للطلب الأول فقط"
    )

    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "كوبون"
        verbose_name_plural = "الكوبونات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active", "start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == DiscountType.PERCENTAGE else ''}"

    @property
    def status(self):
        """Get current coupon status"""
        now = timezone.now()
        if not self.is_active:
            return CouponStatus.INACTIVE
        if (
            self.start_date
            and self.end_date
            and (now < self.start_date or now > self.end_date)
        ):
            return CouponStatus.EXPIRED
        if self.usage_limit and self.times_used >= self.usage_limit:
            return CouponStatus.EXPIRED
        return CouponStatus.ACTIVE

    @property
    def is_valid(self):
        """Check if coupon is currently valid"""
        return self.status == CouponStatus.ACTIVE

    def calculate_discount(self, order_amount, delivery_fee=Decimal("0")):
        if order_amount < self.minimum_order_amount:
            return Decimal("0")

        if self.discount_type == DiscountType.FREE_DELIVERY:
            return delivery_fee  # ← يرجع قيمة التوصيل كاملة

        elif self.discount_type == DiscountType.PERCENTAGE:
            discount = order_amount * (self.discount_value / 100)
            if self.max_discount:
                discount = min(discount, self.max_discount)

        else:
            discount = min(self.discount_value, order_amount)

        return discount.quantize(Decimal("0.01"))

    def can_be_used_by(self, user, restaurant=None):
        """
        Check if coupon can be used by a specific user.
        Returns (can_use, error_message)
        """
        if not self.is_valid:
            return False, "الكوبون غير صالح"

        # Check restaurant restriction
        if self.restaurant and restaurant and self.restaurant != restaurant:
            return False, "الكوبون غير صالح لهذا المطعم"

        # Check user usage limit
        user_usage = CouponUsage.objects.filter(coupon=self, user=user).count()

        # ✅ أضف هذا: احسب الطلبات النشطة التي تستخدم نفس الكوبون
        from orders.models import Order
        from core.constants import OrderStatus

        active_usage = (
            Order.objects.filter(
                coupon=self,
                user=user,
            )
            .exclude(status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED])
            .count()
        )

        if (user_usage + active_usage) >= self.usage_limit_per_user:
            return False, "لقد استخدمت هذا الكوبون من قبل"

        # Check first order only
        if self.first_order_only:
            has_orders = (
                Order.objects.filter(
                    user=user,
                )
                .exclude(
                    status=OrderStatus.CANCELLED  # فقط الملغي يُستثنى
                )
                .exists()
            )

            if has_orders:
                return False, "هذا الكوبون للطلب الأول فقط"

        return True, None

    def use(self, user, order):
        Coupon.objects.filter(pk=self.pk).update(times_used=F("times_used") + 1)
        CouponUsage.objects.create(
            coupon=self,
            user=user,
            order=order,
            discount_amount=order.discount_amount,  # ← أضف هذا
        )


class CouponUsage(BaseModel):
    """
    Track coupon usage history
    """

    coupon = models.ForeignKey(
        Coupon, on_delete=models.CASCADE, related_name="usages", verbose_name="الكوبون"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coupon_usages",
        verbose_name="المستخدم",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="coupon_usages",
        verbose_name="الطلب",
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="مبلغ الخصم"
    )

    class Meta:
        verbose_name = "استخدام كوبون"
        verbose_name_plural = "استخدامات الكوبونات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} used {self.coupon.code}"
