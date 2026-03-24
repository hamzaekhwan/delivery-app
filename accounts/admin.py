"""
Accounts Admin - Simplified with DriverSession only
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from .models import User, OTP, DriverSession, AdminSession, Hero


# ═══════════════════════════════════════════════════════════
#                    Hero Admin
# ═══════════════════════════════════════════════════════════
@admin.register(Hero)
class HeroAdmin(admin.ModelAdmin):
    list_display = ["number", "name", "is_active", "drivers_count"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    list_editable = ["is_active"]
    ordering = ["number"]

    def drivers_count(self, obj):
        return obj.drivers.count()

    drivers_count.short_description = "عدد السائقين"


# ═══════════════════════════════════════════════════════════
#                    User Admin
# ═══════════════════════════════════════════════════════════
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "phone_number",
        "full_name",
        "role",
        "governorate",
        "is_active",
        "online_status",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_online", "governorate"]
    search_fields = ["phone_number", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("المعلومات الشخصية", {"fields": ("first_name", "last_name", "governorate")}),
        (
            "الدور والصلاحيات",
            {"fields": ("role", "is_active", "is_staff", "is_superuser")},
        ),
        ("حالة السائق", {"fields": ("is_online", "last_online", "hero")}),
        ("التواريخ", {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "first_name",
                    "last_name",
                    "governorate",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    readonly_fields = ["date_joined", "last_login", "last_online"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_active = True
            if obj.role == User.Role.ADMIN:
                obj.is_staff = True
                obj.is_superuser = True
        super().save_model(request, obj, form, change)

    def online_status(self, obj):
        if obj.role not in [User.Role.DRIVER, User.Role.ADMIN] and not obj.is_staff:
            return "-"
        if obj.is_online:
            return format_html(
                '<span style="color: green; font-weight: bold;">🟢 متصل</span>'
            )
        return format_html('<span style="color: gray;">⚪ غير متصل</span>')

    online_status.short_description = "حالة الاتصال"


# ═══════════════════════════════════════════════════════════
#                    Driver Session Admin
# ═══════════════════════════════════════════════════════════
@admin.register(DriverSession)
class DriverSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "driver",
        "date",
        "started_at",
        "ended_at",
        "duration_display",
        "session_status",
    ]
    list_filter = ["date", "is_active", "driver"]
    search_fields = ["driver__phone_number", "driver__first_name", "driver__last_name"]
    date_hierarchy = "date"
    ordering = ["-started_at"]

    readonly_fields = [
        "duration_display",
        "duration_hours",
        "session_status",
    ]

    fieldsets = (
        ("معلومات الجلسة", {"fields": ("driver", "date", "started_at", "ended_at")}),
        (
            "الحالة",
            {
                "fields": (
                    "is_active",
                    "session_status",
                    "duration_seconds",
                    "duration_display",
                    "duration_hours",
                )
            },
        ),
    )

    def session_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">🟢 جلسة نشطة</span>'
            )
        return format_html('<span style="color: gray;">⚪ منتهية</span>')

    session_status.short_description = "حالة الجلسة"

    actions = ["end_active_sessions"]

    @admin.action(description="إنهاء الجلسات النشطة المحددة")
    def end_active_sessions(self, request, queryset):
        count = 0
        for session in queryset.filter(is_active=True):
            session.end_session()
            count += 1
        self.message_user(request, f"تم إنهاء {count} جلسة")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        date_from = getattr(request, "_date_from", "")
        date_to = getattr(request, "_date_to", "")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        date_from = request.GET.get("date_from", "").strip()
        date_to = request.GET.get("date_to", "").strip()
        extra_context["date_from"] = date_from
        extra_context["date_to"] = date_to

        # Remove custom params so Django admin doesn't reject them
        if "date_from" in request.GET or "date_to" in request.GET:
            request.GET = request.GET.copy()
            request.GET.pop("date_from", None)
            request.GET.pop("date_to", None)

        # Store for get_queryset
        request._date_from = date_from
        request._date_to = date_to

        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return response

        agg = qs.aggregate(total_seconds=Sum("duration_seconds"))
        total_seconds = agg["total_seconds"] or 0

        active_qs = qs.filter(is_active=True)
        for s in active_qs.only("started_at"):
            if s.started_at:
                total_seconds += int((timezone.now() - s.started_at).total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        response.context_data["session_stats"] = {
            "total_sessions": qs.count(),
            "active_sessions": active_qs.count(),
            "hours": hours,
            "minutes": minutes,
        }
        return response


# ═══════════════════════════════════════════════════════════
#                    Admin Session Admin
# ═══════════════════════════════════════════════════════════
@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "admin_user",
        "date",
        "started_at",
        "ended_at",
        "duration_display",
        "session_status",
    ]
    list_filter = ["date", "is_active", "admin_user"]
    search_fields = [
        "admin_user__phone_number",
        "admin_user__first_name",
        "admin_user__last_name",
    ]
    date_hierarchy = "date"
    ordering = ["-started_at"]

    readonly_fields = [
        "duration_display",
        "duration_hours",
        "session_status",
    ]

    fieldsets = (
        (
            "معلومات الجلسة",
            {"fields": ("admin_user", "date", "started_at", "ended_at")},
        ),
        (
            "الحالة",
            {
                "fields": (
                    "is_active",
                    "session_status",
                    "duration_seconds",
                    "duration_display",
                    "duration_hours",
                )
            },
        ),
    )

    def session_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">🟢 جلسة نشطة</span>'
            )
        return format_html('<span style="color: gray;">⚪ منتهية</span>')

    session_status.short_description = "حالة الجلسة"

    actions = ["end_active_sessions"]

    @admin.action(description="إنهاء الجلسات النشطة المحددة")
    def end_active_sessions(self, request, queryset):
        count = 0
        for session in queryset.filter(is_active=True):
            session.end_session()
            count += 1
        self.message_user(request, f"تم إنهاء {count} جلسة")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        date_from = getattr(request, "_date_from", "")
        date_to = getattr(request, "_date_to", "")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        date_from = request.GET.get("date_from", "").strip()
        date_to = request.GET.get("date_to", "").strip()
        extra_context["date_from"] = date_from
        extra_context["date_to"] = date_to

        if "date_from" in request.GET or "date_to" in request.GET:
            request.GET = request.GET.copy()
            request.GET.pop("date_from", None)
            request.GET.pop("date_to", None)

        request._date_from = date_from
        request._date_to = date_to

        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return response

        agg = qs.aggregate(total_seconds=Sum("duration_seconds"))
        total_seconds = agg["total_seconds"] or 0

        active_qs = qs.filter(is_active=True)
        for s in active_qs.only("started_at"):
            if s.started_at:
                total_seconds += int((timezone.now() - s.started_at).total_seconds())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        response.context_data["session_stats"] = {
            "total_sessions": qs.count(),
            "active_sessions": active_qs.count(),
            "hours": hours,
            "minutes": minutes,
        }
        return response


# ═══════════════════════════════════════════════════════════
#                    OTP Admin
# ═══════════════════════════════════════════════════════════
@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "otp_type",
        "code",
        "is_used",
        "otp_status",
        "created_at",
        "expires_at",
    ]
    list_filter = ["otp_type", "is_used", "created_at"]
    search_fields = ["user__phone_number", "code"]
    ordering = ["-created_at"]

    readonly_fields = ["code", "created_at", "otp_status"]

    def otp_status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: gray;">✓ مستخدم</span>')
        if not obj.is_valid():
            return format_html('<span style="color: red;">✗ منتهي</span>')
        return format_html('<span style="color: green;">● صالح</span>')

    otp_status.short_description = "الحالة"
