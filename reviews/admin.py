"""
Reviews Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import RestaurantReview, RestaurantReviewImage, DriverReview


# class RestaurantReviewImageInline(admin.TabularInline):
#     model = RestaurantReviewImage
#     extra = 0
#     readonly_fields = ["image_preview"]

#     def image_preview(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
#                 obj.image.url,
#             )
#         return "-"

#     image_preview.short_description = "Preview"


# @admin.register(RestaurantReview)
# class RestaurantReviewAdmin(admin.ModelAdmin):
#     list_display = [
#         "id",
#         "user",
#         "restaurant",
#         "overall_rating",
#         "star_display",
#         "is_approved",
#         "is_hidden",
#         "created_at",
#     ]
#     list_filter = [
#         "overall_rating",
#         "is_approved",
#         "is_hidden",
#         "created_at",
#         "restaurant",
#     ]
#     search_fields = [
#         "user__phone_number",
#         "user__full_name",
#         "restaurant__name",
#         "comment",
#     ]
#     readonly_fields = [
#         "user",
#         "restaurant",
#         "order",
#         "overall_rating",
#         "food_quality_rating",
#         "packaging_rating",
#         "value_rating",
#         "comment",
#         "created_at",
#     ]
#     inlines = [RestaurantReviewImageInline]
#     list_per_page = 25
#     date_hierarchy = "created_at"

#     actions = ["approve_reviews", "hide_reviews", "unhide_reviews"]

#     def star_display(self, obj):
#         stars = "★" * obj.overall_rating + "☆" * (5 - obj.overall_rating)
#         return format_html('<span style="color: #f39c12;">{}</span>', stars)

#     star_display.short_description = "Rating"

#     @admin.action(description="Approve selected reviews")
#     def approve_reviews(self, request, queryset):
#         count = queryset.update(is_approved=True)
#         self.message_user(request, f"{count} reviews approved.")

#     @admin.action(description="Hide selected reviews")
#     def hide_reviews(self, request, queryset):
#         count = queryset.update(is_hidden=True)
#         self.message_user(request, f"{count} reviews hidden.")

#     @admin.action(description="Unhide selected reviews")
#     def unhide_reviews(self, request, queryset):
#         count = queryset.update(is_hidden=False)
#         self.message_user(request, f"{count} reviews unhidden.")


@admin.register(DriverReview)
class DriverReviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "driver",
        "overall_rating",
        "star_display",
        "is_approved",
        "is_hidden",
        "created_at",
    ]
    list_filter = ["overall_rating", "is_approved", "is_hidden", "created_at", "driver"]
    search_fields = [
        "user__phone_number",
        "user__full_name",
        "driver__phone_number",
        "driver__full_name",
        "comment",
    ]
    readonly_fields = [
        "user",
        "driver",
        "order",
        "overall_rating",
        "comment",
        "created_at",
    ]
    list_per_page = 25
    date_hierarchy = "created_at"

    actions = ["approve_reviews", "hide_reviews", "unhide_reviews"]

    def star_display(self, obj):
        stars = "★" * obj.overall_rating + "☆" * (5 - obj.overall_rating)
        return format_html('<span style="color: #f39c12;">{}</span>', stars)

    star_display.short_description = "Rating"

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} reviews approved.")

    @admin.action(description="Hide selected reviews")
    def hide_reviews(self, request, queryset):
        count = queryset.update(is_hidden=True)
        self.message_user(request, f"{count} reviews hidden.")

    @admin.action(description="Unhide selected reviews")
    def unhide_reviews(self, request, queryset):
        count = queryset.update(is_hidden=False)
        self.message_user(request, f"{count} reviews unhidden.")
