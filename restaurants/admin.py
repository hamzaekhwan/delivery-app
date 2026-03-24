"""
Restaurant Admin - Admin configuration for restaurant models
"""

from django.contrib import admin
from .models import Restaurant, RestaurantCategory, RestaurantWorkingHours


class RestaurantWorkingHoursInline(admin.TabularInline):
    model = RestaurantWorkingHours
    extra = 0
    max_num = 7


@admin.register(RestaurantCategory)
class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "order", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "name_en"]
    list_editable = ["is_active", "order"]
    ordering = ["order", "name"]


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "restaurant_type",
        "get_categories",
        "is_active",
        "is_open",
        "minimum_order_amount",
        "delivery_fee",
        "average_rating",
        "total_orders",
        "is_featured",
    ]
    list_filter = [
        "restaurant_type",
        "categories",
        "is_active",
        "is_open",
        "is_featured",
        "has_discount",
        "created_at",
    ]
    search_fields = ["name", "name_en", "description", "address"]
    list_editable = ["is_active", "is_open", "is_featured"]
    readonly_fields = [
        "total_orders",
        "average_rating",
        "total_reviews",
        "created_at",
        "updated_at",
    ]
    inlines = [RestaurantWorkingHoursInline]

    fieldsets = (
        (
            "المعلومات الأساسية",
            {"fields": ("name", "name_en", "slug", "description", "description_en")},
        ),
        ("الصور", {"fields": ("logo", "cover_image")}),
        ("النوع والتصنيف", {"fields": ("restaurant_type", "categories")}),
        ("الموقع والتواصل", {"fields": ("address", "latitude", "longitude", "phone")}),
        (
            "الحالة وساعات العمل",
            {"fields": ("is_active", "is_open", "opening_time", "closing_time")},
        ),
        (
            "إعدادات الطلب",
            {
                "fields": (
                    "minimum_order_amount",
                    "delivery_fee",
                    "delivery_time_estimate",
                    "app_discount_percentage",
                )
            },
        ),
        (
            "الخصومات",
            {
                "fields": (
                    "has_discount",
                    "discount_percentage",
                    "discount_start_time",
                    "discount_end_time",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "الإحصائيات",
            {
                "fields": ("total_orders", "average_rating", "total_reviews"),
                "classes": ("collapse",),
            },
        ),
        ("التميز", {"fields": ("is_featured",)}),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    filter_horizontal = ["categories"]

    actions = [
        "make_featured",
        "remove_featured",
        "open_restaurants",
        "close_restaurants",
    ]

    @admin.display(description="التصنيفات")
    def get_categories(self, obj):
        return ", ".join(c.name for c in obj.categories.all())

    @admin.action(description="تمييز المطاعم المحددة")
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="إزالة التمييز من المطاعم المحددة")
    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="فتح المطاعم المحددة")
    def open_restaurants(self, request, queryset):
        queryset.update(is_open=True)

    @admin.action(description="إغلاق المطاعم المحددة")
    def close_restaurants(self, request, queryset):
        queryset.update(is_open=False)


@admin.register(RestaurantWorkingHours)
class RestaurantWorkingHoursAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "day", "opening_time", "closing_time", "is_closed"]
    list_filter = ["day", "is_closed", "restaurant"]
    search_fields = ["restaurant__name"]
