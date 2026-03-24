"""
Menu Admin - Admin configuration for menu models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    MenuCategory,
    MenuSubCategory,
    Product,
    ProductImage,
    ProductVariation,
    ProductAddon,
)


class MenuSubCategoryInline(admin.TabularInline):
    model = MenuSubCategory
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "products_count", "is_active", "order"]
    list_filter = ["restaurant", "is_active"]
    search_fields = ["name", "name_en", "restaurant__name"]
    list_editable = ["is_active", "order"]
    inlines = [MenuSubCategoryInline]
    autocomplete_fields = ["restaurant"]

    def products_count(self, obj):
        count = obj.products.count()
        return format_html(
            '<span style="background:#17a2b8;color:white;padding:2px 8px;border-radius:3px;">{}</span>',
            count,
        )

    products_count.short_description = "عدد المنتجات"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "image_preview",
        "name",
        "restaurant",
        "category",
        "price_display",  # يعرض السعر الأساسي
        "discounted_price_display",  # يعرض سعر بعد الخصم إن وُجد
        "discount_badge",  # شارة توضح حالة الخصم
        "availability_badge",
        "base_price",
        "is_available",
    ]
    list_filter = [
        "restaurant",
        "category",
        "is_available",
        "is_featured",
        "is_popular",
        "has_discount",  # فلتر جديد للخصم
    ]
    search_fields = ["name", "name_en", "description", "restaurant__name"]
    list_editable = ["base_price", "is_available"]

    readonly_fields = [
        "image_preview_large",
        "discount_status_display",  # حقل قراءة فقط يوضح حالة الخصم الآن
        "created_at",
        "updated_at",
    ]
    inlines = [ProductImageInline]
    autocomplete_fields = ["restaurant", "category"]
    list_per_page = 30

    fieldsets = (
        (
            "المعلومات الأساسية",
            {
                "fields": (
                    "restaurant",
                    "category",
                    "subcategory",
                    "name",
                    "name_en",
                    "description",
                    "description_en",
                    "image",
                    "image_preview_large",
                )
            },
        ),
        ("السعر", {"fields": ("base_price",)}),
        (
            "🏷️ الخصم",
            {
                "fields": (
                    "has_discount",
                    "discount_type",
                    "discount_value",
                    "discount_start",
                    "discount_end",
                    "discount_status_display",  # readonly - يظهر الحالة الفعلية
                ),
                "classes": ("collapse",),
                "description": (
                    "فعّل الخصم ثم حدد نوعه (نسبة مئوية أو مبلغ ثابت) وقيمته. "
                    "يمكنك تحديد فترة زمنية للخصم أو تركها فارغة ليكون الخصم دائماً."
                ),
            },
        ),
        (
            "الحالة والترتيب",
            {"fields": ("is_available", "is_featured", "is_popular", "order")},
        ),
        (
            "معلومات إضافية",
            {
                "fields": ("calories", "preparation_time"),
                "classes": ("collapse",),
            },
        ),
        (
            "معلومات النظام",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "make_available",
        "make_unavailable",
        "make_featured",
        "activate_discount",  # تفعيل الخصم دفعة واحدة
        "deactivate_discount",  # إلغاء الخصم دفعة واحدة
    ]

    # ──────────────────────────────────────────
    # Display helpers
    # ──────────────────────────────────────────

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:5px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "صورة"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:200px;max-height:200px;border-radius:8px;" />',
                obj.image.url,
            )
        return "لا توجد صورة"

    image_preview_large.short_description = "معاينة الصورة"

    def price_display(self, obj):
        """السعر الأساسي - يُشطب إن كان الخصم نشطاً"""
        if obj.is_discount_active:
            return format_html(
                '<span style="color:#999;text-decoration:line-through;">{}</span>',
                f"{obj.base_price:,.0f}",
            )
        return format_html(
            '<strong style="color:#28a745;">{}</strong>',
            f"{obj.base_price:,.0f}",
        )

    price_display.short_description = "السعر الأساسي"

    def discounted_price_display(self, obj):
        """السعر بعد الخصم - يظهر فقط إن كان الخصم نشطاً"""
        if obj.is_discount_active:
            return format_html(
                '<strong style="color:#e83e8c;">{}</strong>',
                f"{obj.current_price:,.0f}",
            )
        return "—"

    discounted_price_display.short_description = "بعد الخصم"

    def discount_badge(self, obj):
        """شارة ملونة توضح حالة الخصم"""
        if not obj.has_discount:
            return "—"
        if obj.is_discount_active:
            label = f"-{obj.discount_value:,.0f}"
            label += "%" if obj.discount_type == "percentage" else " ل.س"
            return format_html(
                '<span style="background:#e83e8c;color:white;padding:2px 8px;'
                'border-radius:3px;font-weight:bold;">{}</span>',
                label,
            )
        # has_discount=True لكن ليس في الفترة النشطة
        return format_html(
            '<span style="background:#ffc107;color:#333;padding:2px 8px;border-radius:3px;">معلّق</span>'
        )

    discount_badge.short_description = "الخصم"

    def discount_status_display(self, obj):
        """حقل readonly داخل النموذج يوضح الحالة الكاملة"""
        if not obj.has_discount:
            return format_html('<span style="color:#6c757d;">لا يوجد خصم مفعّل</span>')
        now = timezone.now()
        parts = []

        if obj.discount_start and obj.discount_start > now:
            parts.append(
                f"⏳ لم يبدأ بعد — يبدأ في {obj.discount_start.strftime('%Y-%m-%d %H:%M')}"
            )
        elif obj.discount_end and obj.discount_end < now:
            parts.append(
                f"⛔ انتهى الخصم في {obj.discount_end.strftime('%Y-%m-%d %H:%M')}"
            )
        elif obj.is_discount_active:
            end_str = (
                obj.discount_end.strftime("%Y-%m-%d %H:%M")
                if obj.discount_end
                else "بلا تاريخ انتهاء"
            )
            parts.append(f"✅ الخصم نشط الآن — ينتهي: {end_str}")
            parts.append(
                f"السعر الحالي: {obj.current_price:,.0f} (وفر: {obj.discount_amount:,.0f})"
            )

        return format_html("<br>".join(parts)) if parts else "—"

    discount_status_display.short_description = "حالة الخصم الآن"

    def availability_badge(self, obj):
        if obj.is_available:
            return format_html(
                '<span style="background:#28a745;color:white;padding:2px 8px;border-radius:3px;">متوفر</span>'
            )
        return format_html(
            '<span style="background:#dc3545;color:white;padding:2px 8px;border-radius:3px;">غير متوفر</span>'
        )

    availability_badge.short_description = "الحالة"

    # ──────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────

    @admin.action(description="جعل المنتجات متوفرة")
    def make_available(self, request, queryset):
        count = queryset.update(is_available=True)
        self.message_user(request, f"تم تفعيل {count} منتج")

    @admin.action(description="جعل المنتجات غير متوفرة")
    def make_unavailable(self, request, queryset):
        count = queryset.update(is_available=False)
        self.message_user(request, f"تم تعطيل {count} منتج")

    @admin.action(description="تمييز المنتجات")
    def make_featured(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"تم تمييز {count} منتج")

    @admin.action(description="🏷️ تفعيل الخصم على المنتجات المحددة")
    def activate_discount(self, request, queryset):
        count = queryset.update(has_discount=True)
        self.message_user(request, f"تم تفعيل الخصم على {count} منتج")

    @admin.action(description="❌ إلغاء الخصم على المنتجات المحددة")
    def deactivate_discount(self, request, queryset):
        count = queryset.update(has_discount=False)
        self.message_user(request, f"تم إلغاء الخصم على {count} منتج")
