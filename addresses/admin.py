from django.contrib import admin
from django.utils.html import format_html
from .models import Address, Governorate, Area


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "governorate",
        "is_current_badge",
        "created_at",
    ]
    list_filter = ["governorate", "is_current", "created_at"]
    search_fields = [
        "user__phone_number",
        "user__first_name",
        "title",
        "area__name",
        "area__name_en",
        "governorate__name",
        "governorate__name_en",
        "street",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        ("المستخدم", {"fields": ("user", "title")}),
        ("تفاصيل العنوان", {"fields": ("governorate", "area", "street")}),
        (
            "تفاصيل إضافية",
            {
                "fields": (
                    "building_number",
                    "floor",
                    "apartment",
                    "landmark",
                    "additional_notes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "الموقع الجغرافي",
            {"fields": ("latitude", "longitude"), "classes": ("collapse",)},
        ),
        ("الإعدادات", {"fields": ("is_current",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    def is_current_badge(self, obj):
        if obj.is_current:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 15px; font-size: 11px;">✓ حالي</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 10px; '
            'border-radius: 15px; font-size: 11px;">-</span>'
        )

    is_current_badge.short_description = "العنوان الحالي"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "governorate")
    list_filter = ("governorate",)
    prepopulated_fields = {"slug": ("name",)}

