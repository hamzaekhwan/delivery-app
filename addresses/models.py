from django.db import models
from django.conf import settings


class Governorate(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المحافظة")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(unique=True, verbose_name="المعرف")

    class Meta:
        verbose_name = "محافظة"
        verbose_name_plural = "المحافظات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Area(models.Model):
    governorate = models.ForeignKey(
        Governorate,
        on_delete=models.CASCADE,
        related_name="areas",
        verbose_name="المحافظة",
    )
    name = models.CharField(max_length=100, verbose_name="اسم المنطقة")
    name_en = models.CharField(
        max_length=100, blank=True, verbose_name="الاسم (إنجليزي)"
    )
    slug = models.SlugField(verbose_name="المعرف")

    class Meta:
        verbose_name = "منطقة"
        verbose_name_plural = "المناطق"
        ordering = ["name"]
        unique_together = ("governorate", "slug")

    def __str__(self):
        return f"{self.name} - {self.governorate.name}"


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="المستخدم",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="عنوان المكان",
        help_text="مثال: المنزل، العمل",
    )

    governorate = models.ForeignKey(
        Governorate,
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="المحافظة",
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="المنطقة / المدينة",
    )
    street = models.CharField(max_length=200, verbose_name="الشارع", blank=True)

    building_number = models.CharField(
        max_length=50, blank=True, verbose_name="رقم البناية"
    )
    floor = models.CharField(max_length=20, blank=True, verbose_name="الطابق")
    apartment = models.CharField(max_length=50, blank=True, verbose_name="رقم الشقة")

    landmark = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="علامة مميزة",
        help_text="مثال: قرب مسجد",
    )

    additional_notes = models.TextField(blank=True, verbose_name="ملاحظات إضافية")

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط العرض"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="خط الطول"
    )

    is_current = models.BooleanField(default=False, verbose_name="العنوان الحالي")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"
        ordering = ["-is_current", "-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.phone_number}"

    @property
    def full_address(self):
        parts = [
            self.governorate.name,
            self.area.name,
            self.street,
        ]
        if self.building_number:
            parts.append(f"بناية {self.building_number}")
        if self.floor:
            parts.append(f"طابق {self.floor}")
        if self.apartment:
            parts.append(f"شقة {self.apartment}")
        return "، ".join(filter(None, parts))

    def save(self, *args, **kwargs):
        if self.is_current:
            Address.objects.filter(user=self.user, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)

        if not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_current = True

        super().save(*args, **kwargs)
