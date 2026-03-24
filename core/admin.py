"""
Core Admin - Admin configuration for core models
"""

from django.contrib import admin
from .models import Banner, AppConfiguration


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "banner_type",
        "is_active",
        "is_currently_active",
        "order",
        "start_date",
        "end_date",
        "created_at",
    ]
    list_filter = ["banner_type", "is_active", "created_at"]
    search_fields = ["title", "subtitle"]
    list_editable = ["is_active", "order"]
    ordering = ["order", "-created_at"]
    readonly_fields = ["created_at", "updated_at", "is_currently_active"]

    fieldsets = (
        (
            "المعلومات الأساسية",
            {"fields": ("title", "subtitle", "image", "banner_type", "link")},
        ),
        ("التفعيل", {"fields": ("is_active", "start_date", "end_date", "order")}),
        (
            "معلومات النظام",
            {
                "fields": ("created_at", "updated_at", "is_currently_active"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(AppConfiguration)
class AppConfigurationAdmin(admin.ModelAdmin):
    list_display = ["__str__", "app_version", "maintenance_mode"]

    fieldsets = (
        (
            "إعدادات التوصيل",
            {
                "fields": (
                    "base_delivery_fee",
                    "free_distance_km",
                    "per_km_fee",
                    "max_delivery_fee",
                    "max_delivery_radius_km",
                    "free_delivery_threshold",
                )
            },
        ),
        ("إعدادات الطلب", {"fields": ("min_order_amount", "preparation_lead_minutes")}),
        (
            "إعدادات السائق",
            {"fields": ("driver_search_radius_km", "driver_accept_timeout_seconds", "min_online_drivers")},
        ),
        (
            "إعدادات الصفحة الرئيسية",
            {
                "fields": (
                    "recommended_weight_rating",
                    "recommended_weight_orders",
                    "recommended_weight_recent",
                    "recent_orders_days",
                )
            },
        ),
        (
            "إعدادات عامة",
            {"fields": ("app_version", "maintenance_mode", "maintenance_message")},
        ),
    )

    def has_add_permission(self, request):
        # Only allow one configuration
        return not AppConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
