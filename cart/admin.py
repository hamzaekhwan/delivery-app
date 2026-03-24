"""
Cart Admin - Updated for multiple carts support
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["unit_price", "addons_total", "total_price"]
    show_change_link = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "restaurant",
        "items_count",
        "total",
        "expiry_status",
        "expires_at",
        "updated_at",
    ]
    list_filter = ["restaurant", "created_at", "expires_at"]
    search_fields = ["user__phone_number", "user__email", "restaurant__name"]
    readonly_fields = [
        "items_count",
        "subtotal",
        "delivery_fee",
        "discount_amount",
        "total",
        "expiry_status",
        "time_remaining",
    ]
    inlines = [CartItemInline]
    date_hierarchy = "created_at"

    fieldsets = (
        ("معلومات السلة", {"fields": ("user", "restaurant", "notes")}),
        ("الصلاحية", {"fields": ("expires_at", "expiry_status", "time_remaining")}),
        ("الكوبون", {"fields": ("coupon",)}),
        (
            "الحساب",
            {
                "fields": (
                    "items_count",
                    "subtotal",
                    "delivery_fee",
                    "discount_amount",
                    "total",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def expiry_status(self, obj):
        if obj.is_expired:
            return format_html(
                '<span style="color: red; font-weight: bold;">⛔ منتهية</span>'
            )
        else:
            return format_html(
                '<span style="color: green; font-weight: bold;">✅ نشطة</span>'
            )

    expiry_status.short_description = "الحالة"

    def time_remaining(self, obj):
        if obj.is_expired:
            return "منتهية"
        remaining = obj.time_remaining
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours} ساعة و {minutes} دقيقة"

    time_remaining.short_description = "الوقت المتبقي"

    actions = ["refresh_expiry", "delete_expired"]

    @admin.action(description="تجديد صلاحية السلات المحددة")
    def refresh_expiry(self, request, queryset):
        for cart in queryset:
            cart.refresh_expiry()
        self.message_user(request, f"تم تجديد صلاحية {queryset.count()} سلة")

    @admin.action(description="حذف السلات المنتهية")
    def delete_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f"تم حذف {count} سلة منتهية")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "cart",
        "product",
        "quantity",
        "unit_price",
        "total_price",
    ]
    list_filter = ["cart__restaurant", "created_at"]
    search_fields = ["product__name", "cart__user__phone_number"]
    readonly_fields = ["unit_price", "total_price"]
