"""
Coupon Admin - Admin configuration for coupon models
"""

from django.contrib import admin
from .models import Coupon, CouponUsage


class CouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ["user", "order", "discount_amount", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "restaurant",
        "is_active",
        "status",
        "times_used",
        "usage_limit",
        "start_date",
        "end_date",
    ]
    list_filter = [
        "is_active",
        "discount_type",
        "restaurant",
        "first_order_only",
        "start_date",
        "end_date",
    ]
    search_fields = ["code", "description"]
    readonly_fields = ["times_used", "status", "created_at", "updated_at"]
    list_editable = ["is_active"]
    inlines = [CouponUsageInline]
    autocomplete_fields = ["restaurant"]

    fieldsets = (
        ("معلومات الكوبون", {"fields": ("code", "description")}),
        ("الخصم", {"fields": ("discount_type", "discount_value", "max_discount")}),
        ("الصلاحية", {"fields": ("start_date", "end_date", "is_active", "status")}),
        (
            "حدود الاستخدام",
            {"fields": ("usage_limit", "usage_limit_per_user", "times_used")},
        ),
        (
            "الشروط",
            {"fields": ("minimum_order_amount", "restaurant", "first_order_only")},
        ),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
