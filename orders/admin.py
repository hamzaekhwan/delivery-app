"""
Orders Admin - Complete order management in admin panel
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    DriverOrderRequest,
    OrderDeliveryReport,
    OrderDeliveryReportImage,
)
from core.constants import OrderStatus


# ═══════════════════════════════════════════════════════════
#                    Custom Filters
# ═══════════════════════════════════════════════════════════


class OrderDateRangeFilter(admin.SimpleListFilter):
    """فلتر الفترة الزمنية"""

    title = "الفترة الزمنية"
    parameter_name = "date_range"

    def lookups(self, request, model_admin):
        return [
            ("today", "📅 اليوم"),
            ("yesterday", "📅 أمس"),
            ("week", "📆 هذا الأسبوع"),
            ("month", "🗓️ هذا الشهر"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today":
            return queryset.filter(created_at__date=now.date())
        if self.value() == "yesterday":
            yesterday = now.date() - timedelta(days=1)
            return queryset.filter(created_at__date=yesterday)
        if self.value() == "week":
            return queryset.filter(created_at__gte=now - timedelta(days=7))
        if self.value() == "month":
            return queryset.filter(created_at__gte=now - timedelta(days=30))
        return queryset


class DriverFilter(admin.SimpleListFilter):
    """فلتر حسب سائق معين"""

    title = "السائق"
    parameter_name = "driver_id"

    def lookups(self, request, model_admin):
        from accounts.models import User

        drivers = User.objects.filter(
            role="driver",
            is_active=True,
        ).order_by("first_name")

        result = [("unassigned", "❌ بدون سائق")]
        for driver in drivers:
            is_online = getattr(driver, "is_online", False)
            dot = "🟢" if is_online else "⚫"
            name = getattr(driver, "full_name", None) or driver.phone_number
            result.append((str(driver.id), f"{dot} {name}"))
        return result

    def queryset(self, request, queryset):
        if self.value() == "unassigned":
            return queryset.filter(driver__isnull=True)
        if self.value():
            return queryset.filter(driver_id=self.value())
        return queryset


# ═══════════════════════════════════════════════════════════
#                    Inlines
# ═══════════════════════════════════════════════════════════


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [
        "product",
        "quantity",
        "unit_price",
        "total_price",
        "special_instructions",
    ]
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "notes", "created_at"]
    can_delete = False
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


class DriverOrderRequestInline(admin.TabularInline):
    model = DriverOrderRequest
    extra = 0
    readonly_fields = [
        "driver",
        "action",
        "distance_km",
        "sent_at",
        "responded_at",
    ]
    can_delete = False


class OrderDeliveryReportInline(admin.StackedInline):
    model = OrderDeliveryReport
    extra = 0
    readonly_fields = ["driver", "notes", "created_at", "report_images_preview"]
    can_delete = False
    verbose_name = "تقرير التسليم"
    verbose_name_plural = "تقرير التسليم"

    def report_images_preview(self, obj):
        images = obj.images.all()
        if not images:
            return "لا توجد صور"
        html = ""
        for img in images:
            caption = img.caption or ""
            html += (
                f'<div style="display:inline-block; margin:4px; text-align:center;">'
                f'<img src="{img.image.url}" style="max-height:100px; border-radius:4px;"/>'
                f"<br><small>{caption}</small></div>"
            )
        return format_html(html)

    report_images_preview.short_description = "الصور"

    def has_add_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════
#                    Order Admin
# ═══════════════════════════════════════════════════════════


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/orders/order/change_list.html"
    list_display = [
        "order_number",
        "order_type_badge",
        "user",
        "restaurant",
        "status_badge",
        "original_price_display",
        "discount_display",
        "subtotal_display",
        "delivery_fee_display",
        "total_display",
        "restaurant_total_display",
        "app_revenue_display",
        "driver_info",
        "created_at",
    ]
    list_filter = [
        "status",
        OrderDateRangeFilter,
        DriverFilter,
        "is_price_pending",
        "is_manual",
        "payment_method",
        "payment_status",
        "is_scheduled",
        "restaurant",
        "created_at",
    ]
    search_fields = [
        "order_number",
        "chat_order_id",
        "user__phone_number",
        "user__first_name",
        "restaurant__name",
        "driver__phone_number",
        "driver__first_name",
        "contact_phone",
        "description",
    ]
    readonly_fields = [
        "order_number",
        "user",
        "restaurant",
        "delivery_address",
        "driver",
        "restaurant_snapshot",
        "address_snapshot",
        "items_snapshot",
        "price_pending_badge",
        "placed_at",
        "preparing_at",
        "picked_at",
        "delivered_at",
        "cancelled_at",
        "items_count",
        "created_at",
        "updated_at",
        "created_by",
    ]
    raw_id_fields = ["user", "restaurant", "driver", "delivery_address", "coupon"]
    date_hierarchy = "created_at"
    inlines = [
        OrderItemInline,
        OrderStatusHistoryInline,
        DriverOrderRequestInline,
        OrderDeliveryReportInline,
    ]

    fieldsets = (
        (
            "معلومات الطلب",
            {
                "fields": (
                    "order_number",
                    "chat_order_id",
                    "is_manual",
                    "user",
                    "restaurant",
                    "restaurant_name_manual",
                    "driver",
                    "delivery_address",
                    "status",
                    "price_pending_badge",
                    "items_count",
                    "created_by",
                )
            },
        ),
        (
            "وصف الطلب اليدوي",
            {
                "fields": ("description", "delivery_address_text"),
                "classes": ["collapse"],
                "description": "يُستخدم فقط للطلبات اليدوية التي يُنشئها الأدمن",
            },
        ),
        (
            "التواصل والجدولة",
            {"fields": ("contact_phone", "is_scheduled", "scheduled_delivery_time")},
        ),
        (
            "الدفع",
            {
                "fields": (
                    "payment_method",
                    "payment_status",
                    "subtotal",
                    "delivery_fee",
                    "discount_amount",
                    "total",
                    "app_discount_percentage",
                    "restaurant_total",
                    "coupon",
                )
            },
        ),
        (
            "الأوقات",
            {
                "fields": (
                    "placed_at",
                    "preparing_at",
                    "picked_at",
                    "delivered_at",
                    "cancelled_at",
                    "estimated_delivery_time",
                ),
                "classes": ["collapse"],
            },
        ),
        (
            "Snapshots",
            {
                "fields": ("restaurant_snapshot", "address_snapshot", "items_snapshot"),
                "classes": ["collapse"],
            },
        ),
        (
            "ملاحظات",
            {
                "fields": (
                    "notes",
                    "special_instructions",
                    "cancellation_reason",
                    "cancelled_by",
                ),
                "classes": ["collapse"],
            },
        ),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ["collapse"]},
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("coupon")
        date_from = getattr(request, "_date_from", "")
        date_to = getattr(request, "_date_to", "")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
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
            delivered_filter = Q(status=OrderStatus.DELIVERED)
            totals = qs.aggregate(
                total_sum=Sum("total", filter=delivered_filter),
                subtotal_sum=Sum("subtotal", filter=delivered_filter),
                restaurant_total_sum=Sum("restaurant_total", filter=delivered_filter),
                delivery_fee_sum=Sum("delivery_fee", filter=delivered_filter),
                discount_sum=Sum("discount_amount", filter=delivered_filter),
                orders_count=Count("id"),
                delivered_count=Count("id", filter=delivered_filter),
                with_driver=Count("id", filter=Q(driver__isnull=False)),
                without_driver=Count(
                    "id",
                    filter=Q(
                        driver__isnull=True,
                        status__in=[OrderStatus.PLACED, OrderStatus.PREPARING],
                    ),
                ),
            )
            total_sum = float(totals["total_sum"] or 0)
            subtotal_sum = float(totals["subtotal_sum"] or 0)
            restaurant_total_sum = float(totals["restaurant_total_sum"] or 0)
            delivery_fee_sum = float(totals["delivery_fee_sum"] or 0)

            # خصم الكوبون الحقيقي = (subtotal + delivery_fee) - total
            # لأن total = subtotal + delivery_fee - coupon_discount
            coupon_discount_sum = (subtotal_sum + delivery_fee_sum) - total_sum

            # ربح التطبيق = عمولة من المنتجات + رسوم التوصيل − خصم الكوبونات
            # عمولة المنتجات = subtotal - restaurant_total (بتكون 0 لما الخصم للزبون من المطعم)
            app_revenue = (subtotal_sum - restaurant_total_sum) + delivery_fee_sum - coupon_discount_sum

            response.context_data["totals_summary"] = {
                "total_sum": f"{total_sum:,.0f}",
                "subtotal_sum": f"{subtotal_sum:,.0f}",
                "restaurant_total_sum": f"{restaurant_total_sum:,.0f}",
                "delivery_fee_sum": f"{delivery_fee_sum:,.0f}",
                "discount_sum": f"{float(totals['discount_sum'] or 0):,.0f}",
                "coupon_discount_sum": f"{coupon_discount_sum:,.0f}",
                "app_revenue": f"{app_revenue:,.0f}",
                "orders_count": totals["orders_count"],
                "delivered_count": totals["delivered_count"],
                "with_driver": totals["with_driver"],
                "without_driver": totals["without_driver"],
            }
        except (AttributeError, KeyError):
            pass
        return response

    # ─── badges ───────────────────────────────────────────

    def status_badge(self, obj):
        colors = {
            OrderStatus.DRAFT: "#6c757d",
            OrderStatus.PLACED: "#007bff",
            OrderStatus.PREPARING: "#ffc107",
            OrderStatus.PICKED: "#20c997",
            OrderStatus.DELIVERED: "#28a745",
            OrderStatus.CANCELLED: "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "الحالة"

    def price_pending_badge(self, obj):
        if obj.is_price_pending:
            return format_html(
                '<span style="background-color: #fd7e14; color: white; padding: 3px 10px; border-radius: 3px;">Pending</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Fixed</span>'
        )

    price_pending_badge.short_description = "السعر"

    def driver_info(self, obj):
        if not obj.driver:
            return format_html(
                '<span style="color:#dc3545; font-size:12px;">⚠️ بدون سائق</span>'
            )
        is_online = getattr(obj.driver, "is_online", False)
        dot_color = "#28a745" if is_online else "#adb5bd"
        dot_title = "أون لاين" if is_online else "أوف لاين"
        name = getattr(obj.driver, "full_name", None) or obj.driver.phone_number
        return format_html(
            '<span title="{}" style="display:inline-flex; align-items:center; gap:5px;">'
            '<span style="width:9px; height:9px; border-radius:50%; '
            'background-color:{}; display:inline-block;"></span>'
            "{}</span>",
            dot_title,
            dot_color,
            name,
        )

    driver_info.short_description = "السائق"

    def is_scheduled_badge(self, obj):
        if obj.is_scheduled:
            return format_html(
                '<span style="background-color: #6f42c1; color: white; '
                'padding: 3px 8px; border-radius: 3px;" title="{}">⏰ مجدول</span>',
                obj.scheduled_delivery_time.strftime("%Y-%m-%d %H:%M")
                if obj.scheduled_delivery_time
                else "",
            )
        return format_html('<span style="color: #6c757d;">فوري</span>')

    is_scheduled_badge.short_description = "نوع التوصيل"

    def _safe(self, val):
        """Return Decimal 0 if value is None"""
        return val if val is not None else Decimal("0")

    def original_price_display(self, obj):
        """سعر المنتجات الأصلي قبل أي خصم"""
        subtotal = self._safe(obj.subtotal)
        discount = self._safe(obj.discount_amount)
        delivery = self._safe(obj.delivery_fee)
        total = self._safe(obj.total)

        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">ملغي</span>')

        coupon_discount = subtotal + delivery - total
        product_discount = discount - coupon_discount
        original = subtotal + max(product_discount, Decimal("0"))

        if original > subtotal:
            return format_html(
                '<span style="font-size:12px; color:#546e7a;">'
                '<s style="color:#adb5bd;">{}</s> {}</span>',
                f"{original:,.0f}",
                f"{subtotal:,.0f}",
            )
        return format_html(
            '<span style="font-size:12px; color:#546e7a;">{}</span>',
            f"{subtotal:,.0f}",
        )

    original_price_display.short_description = "المنتجات"

    def subtotal_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')
        return format_html(
            '<span style="font-size:12px; color:#1565c0; font-weight:600;">{}</span>',
            f"{self._safe(obj.subtotal):,.0f}",
        )

    subtotal_display.short_description = "بعد الخصم"

    def delivery_fee_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')
        fee = self._safe(obj.delivery_fee)
        if fee > 0:
            return format_html(
                '<span style="color:#00695c; font-size:12px;">{}</span>',
                f"{fee:,.0f}",
            )
        return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')

    delivery_fee_display.short_description = "التوصيل"

    def discount_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')

        discount = self._safe(obj.discount_amount)
        if discount <= 0:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')

        subtotal = self._safe(obj.subtotal)
        delivery = self._safe(obj.delivery_fee)
        total = self._safe(obj.total)

        coupon_discount = subtotal + delivery - total
        product_discount = discount - coupon_discount

        parts = []
        if product_discount > 0:
            parts.append(f'<span style="color:#e65100;" title="خصم المطعم">🏷️ -{product_discount:,.0f}</span>')
        if coupon_discount > 0:
            code = obj.coupon.code if obj.coupon else "كوبون"
            parts.append(f'<span style="color:#6a1b9a;" title="{code}">🎟️ -{coupon_discount:,.0f}</span>')

        if not parts:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')

        return format_html(
            '<span style="font-size:11px; line-height:1.6;">{}</span>',
            format_html("<br>".join(parts)),
        )

    discount_display.short_description = "الخصم"

    def total_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html(
                '<span style="font-size:12px; color:#adb5bd; '
                'text-decoration:line-through;">ملغي</span>'
            )
        return format_html(
            '<span style="font-size:13px; font-weight:700; color:#fff; '
            'background:#1a237e; padding:3px 8px; border-radius:4px;">{}</span>',
            f"{self._safe(obj.total):,.0f}",
        )

    total_display.short_description = "الإجمالي"

    def restaurant_total_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')
        pct = self._safe(obj.app_discount_percentage)
        rest_total = self._safe(obj.restaurant_total)
        if pct > 0:
            return format_html(
                '<span style="font-size:12px;" title="بعد خصم {}% عمولة">{}</span>',
                f"{pct:,.0f}",
                f"{rest_total:,.0f}",
            )
        return format_html(
            '<span style="font-size:12px;">{}</span>',
            f"{rest_total:,.0f}",
        )

    restaurant_total_display.short_description = "للمطعم"

    def app_revenue_display(self, obj):
        if obj.status == OrderStatus.CANCELLED:
            return format_html('<span style="color:#adb5bd; font-size:12px;">—</span>')

        subtotal = self._safe(obj.subtotal)
        rest_total = self._safe(obj.restaurant_total)
        delivery = self._safe(obj.delivery_fee)
        total = self._safe(obj.total)

        commission = subtotal - rest_total
        coupon_discount = subtotal + delivery - total
        revenue = commission + delivery - coupon_discount

        if revenue > 0:
            color = "#1b5e20"
            bg = "#e8f5e9"
        elif revenue < 0:
            color = "#b71c1c"
            bg = "#fce4ec"
        else:
            color = "#546e7a"
            bg = "#eceff1"

        return format_html(
            '<span style="color:{}; background:{}; font-weight:700; '
            'font-size:12px; padding:3px 8px; border-radius:4px;">{}</span>',
            color,
            bg,
            f"{revenue:,.0f}",
        )

    app_revenue_display.short_description = "ربح التطبيق"

    def order_type_badge(self, obj):
        if obj.is_manual:
            return format_html(
                '<span style="background-color: #e83e8c; color: white; '
                'padding: 3px 8px; border-radius: 3px;">📝 يدوي</span>'
            )
        return format_html('<span style="color: #6c757d;">عادي</span>')

    order_type_badge.short_description = "نوع الطلب"

    def chat_order_id_display(self, obj):
        if obj.chat_order_id:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">'
                "💬 {}</span>",
                obj.chat_order_id,
            )
        return "—"

    chat_order_id_display.short_description = "معرف الشات"

    # ─── actions ──────────────────────────────────────────

    actions = [
        "mark_as_preparing",
        "mark_as_picked",
        "mark_as_delivered",
        "mark_as_cancelled",
        "send_to_drivers",
    ]

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields)
    def save_model(self, request, obj, form, change):
        if not change and obj.is_manual:
            obj.created_by = request.user

        if change and "status" in form.changed_data:
            old_status = Order.objects.get(pk=obj.pk).status
            new_status = obj.status
            obj.status = old_status
            super().save_model(request, obj, form, change)

            success, error = obj.update_status(
                new_status, user=request.user, force=True
            )
            if not success:
                from django.contrib import messages

                messages.error(request, f"فشل تغيير الحالة: {error}")
            else:
                from django.contrib import messages

                messages.success(
                    request,
                    f"تم تغيير حالة الطلب #{obj.order_number} "
                    f"من {OrderStatus(old_status).label} إلى {OrderStatus(new_status).label}",
                )
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description='تحديد كـ "جاري التحضير"')
    def mark_as_preparing(self, request, queryset):
        count = 0
        for order in queryset:
            success, _ = order.update_status(
                OrderStatus.PREPARING, request.user, force=True
            )
            if success:
                count += 1
        self.message_user(request, f"تم تحديث {count} طلب إلى جاري التحضير")

    @admin.action(description='تحديد كـ "تم الاستلام"')
    def mark_as_picked(self, request, queryset):
        count = 0
        for order in queryset:
            success, _ = order.update_status(
                OrderStatus.PICKED, request.user, force=True
            )
            if success:
                count += 1
        self.message_user(request, f"تم تحديث {count} طلب إلى تم الاستلام")

    @admin.action(description='تحديد كـ "تم التوصيل"')
    def mark_as_delivered(self, request, queryset):
        count = 0
        for order in queryset:
            success, _ = order.update_status(
                OrderStatus.DELIVERED, request.user, force=True
            )
            if success:
                count += 1
        self.message_user(request, f"تم تحديث {count} طلب إلى تم التوصيل")

    @admin.action(description="إلغاء الطلبات")
    def mark_as_cancelled(self, request, queryset):
        count = 0
        for order in queryset.exclude(
            status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED]
        ):
            success, _ = order.update_status(
                OrderStatus.CANCELLED,
                request.user,
                reason="إلغاء من لوحة الإدارة",
                force=True,
            )
            if success:
                count += 1
        self.message_user(request, f"تم إلغاء {count} طلب")

    @admin.action(description="📤 إرسال الطلب لجميع السائقين")
    def send_to_drivers(self, request, queryset):
        total_requests = 0
        for order in queryset:
            requests = DriverOrderRequest.send_to_all_drivers(order)
            total_requests += len(requests)
        self.message_user(request, f"تم إرسال الطلبات إلى {total_requests} سائق")


# ═══════════════════════════════════════════════════════════
#                    Order Status History Admin
# ═══════════════════════════════════════════════════════════


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["order", "from_status", "to_status", "changed_by", "created_at"]
    list_filter = ["from_status", "to_status", "created_at"]
    search_fields = ["order__order_number"]
    readonly_fields = [
        "order",
        "from_status",
        "to_status",
        "changed_by",
        "notes",
        "created_at",
    ]


# ═══════════════════════════════════════════════════════════
#                    Driver Order Request Admin
# ═══════════════════════════════════════════════════════════


@admin.register(DriverOrderRequest)
class DriverOrderRequestAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "driver",
        "driver_online_status",
        "action_badge",
        "distance_km",
        "sent_at",
        "responded_at",
        "is_expired_display",
    ]
    list_filter = [
        "action",
        OrderDateRangeFilter,
        DriverFilter,
        "sent_at",
    ]
    search_fields = [
        "order__order_number",
        "driver__phone_number",
        "driver__first_name",
    ]
    raw_id_fields = ["order", "driver"]

    def action_badge(self, obj):
        colors = {
            "pending": "#ffc107",
            "accepted": "#28a745",
            "rejected": "#dc3545",
            "expired": "#6c757d",
        }
        color = colors.get(obj.action, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display(),
        )

    action_badge.short_description = "الإجراء"

    def driver_online_status(self, obj):
        is_online = getattr(obj.driver, "is_online", False)
        color = "#28a745" if is_online else "#adb5bd"
        label = "أون لاين" if is_online else "أوف لاين"
        return format_html(
            '<span style="display:inline-flex; align-items:center; gap:5px;">'
            '<span style="width:9px; height:9px; border-radius:50%; '
            'background-color:{}; display:inline-block;"></span>{}</span>',
            color,
            label,
        )

    driver_online_status.short_description = "حالة السائق"

    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">منتهي</span>')
        return format_html('<span style="color: green;">ساري</span>')

    is_expired_display.short_description = "الصلاحية"


# ═══════════════════════════════════════════════════════════
#                    Manual Order (Proxy)
# ═══════════════════════════════════════════════════════════


class ManualOrder(Order):
    class Meta:
        proxy = True
        verbose_name = "طلب يدوي"
        verbose_name_plural = "الطلبات اليدوية"


@admin.register(ManualOrder)
class ManualOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "chat_order_id_display",
        "description_short",
        "status_badge",
        "price_pending_badge",
        "total",
        "driver_info",
        "contact_phone",
        "is_scheduled_badge",
        "created_at",
    ]
    list_filter = [
        "status",
        OrderDateRangeFilter,
        DriverFilter,
        "is_price_pending",
        "is_scheduled",
        "created_at",
    ]
    search_fields = ["order_number", "chat_order_id", "description", "contact_phone"]
    inlines = [OrderStatusHistoryInline, DriverOrderRequestInline]

    add_fieldsets = (
        (
            "تفاصيل الطلب",
            {
                "fields": (
                    "chat_order_id",
                    "description",
                    "delivery_address_text",
                    "contact_phone",
                    "is_price_pending",
                    "total",
                    "payment_method",
                    "scheduled_delivery_time",
                    "notes",
                )
            },
        ),
    )

    change_fieldsets = (
        (
            "تفاصيل الطلب",
            {
                "fields": (
                    "order_number",
                    "chat_order_id",
                    "description",
                    "delivery_address_text",
                    "contact_phone",
                    "total",
                    "payment_method",
                )
            },
        ),
        (
            "الحالة والسائق",
            {"fields": ("status", "is_price_pending", "price_pending_badge", "driver")},
        ),
        (
            "الجدولة",
            {
                "fields": ("is_scheduled", "scheduled_delivery_time"),
                "classes": ["collapse"],
            },
        ),
        (
            "ملاحظات",
            {
                "fields": ("notes",),
                "classes": ["collapse"],
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.change_fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ["order_number", "price_pending_badge"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_manual=True)

    def save_model(self, request, obj, form, change):
        obj.is_manual = True

        if not change:
            obj.status = OrderStatus.PREPARING
            obj.preparing_at = timezone.now()
            obj.placed_at = timezone.now()
            obj.save()

            OrderStatusHistory.objects.create(
                order=obj,
                from_status=OrderStatus.DRAFT,
                to_status=OrderStatus.PREPARING,
                changed_by=request.user,
                notes="طلب يدوي من لوحة الإدارة",
            )
        else:
            if "status" in form.changed_data:
                old_status = ManualOrder.objects.get(pk=obj.pk).status
                new_status = obj.status
                obj.status = old_status
                obj.save()
                obj.update_status(new_status, user=request.user, force=True)
            else:
                obj.save()

    def description_short(self, obj):
        text = obj.description or "—"
        if len(text) > 50:
            text = text[:50] + "..."
        return text

    description_short.short_description = "الوصف"

    def status_badge(self, obj):
        colors = {
            OrderStatus.DRAFT: "#6c757d",
            OrderStatus.PLACED: "#007bff",
            OrderStatus.PREPARING: "#ffc107",
            OrderStatus.PICKED: "#20c997",
            OrderStatus.DELIVERED: "#28a745",
            OrderStatus.CANCELLED: "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "الحالة"

    def price_pending_badge(self, obj):
        if obj.is_price_pending:
            return format_html(
                '<span style="background-color: #fd7e14; color: white; padding: 3px 10px; border-radius: 3px;">Pending</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Fixed</span>'
        )

    price_pending_badge.short_description = "السعر"

    def driver_info(self, obj):
        if not obj.driver:
            return format_html(
                '<span style="color:#dc3545; font-size:12px;">⚠️ بدون سائق</span>'
            )
        is_online = getattr(obj.driver, "is_online", False)
        dot_color = "#28a745" if is_online else "#adb5bd"
        dot_title = "أون لاين" if is_online else "أوف لاين"
        name = getattr(obj.driver, "full_name", None) or obj.driver.phone_number
        return format_html(
            '<span title="{}" style="display:inline-flex; align-items:center; gap:5px;">'
            '<span style="width:9px; height:9px; border-radius:50%; '
            'background-color:{}; display:inline-block;"></span>'
            "{}</span>",
            dot_title,
            dot_color,
            name,
        )

    driver_info.short_description = "السائق"

    def chat_order_id_display(self, obj):
        if obj.chat_order_id:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">'
                "💬 {}</span>",
                obj.chat_order_id,
            )
        return "—"

    chat_order_id_display.short_description = "معرف الشات"

    def is_scheduled_badge(self, obj):
        if obj.is_scheduled:
            return format_html(
                '<span style="background-color: #6f42c1; color: white; '
                'padding: 3px 8px; border-radius: 3px;" title="{}">⏰ مجدول</span>',
                obj.scheduled_delivery_time.strftime("%Y-%m-%d %H:%M")
                if obj.scheduled_delivery_time
                else "",
            )
        return format_html('<span style="color: #6c757d;">فوري</span>')

    is_scheduled_badge.short_description = "نوع التوصيل"


# ═══════════════════════════════════════════════════════════
#                    Delivery Report Admin
# ═══════════════════════════════════════════════════════════


class OrderDeliveryReportImageInline(admin.TabularInline):
    model = OrderDeliveryReportImage
    extra = 0
    readonly_fields = ["image", "caption", "image_preview"]
    can_delete = False

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; border-radius: 4px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "معاينة"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrderDeliveryReport)
class OrderDeliveryReportAdmin(admin.ModelAdmin):
    list_display = ["order", "driver", "notes_short", "created_at"]
    search_fields = ["order__order_number", "driver__phone_number"]
    readonly_fields = ["order", "driver", "notes", "created_at"]
    inlines = [OrderDeliveryReportImageInline]

    def notes_short(self, obj):
        if not obj.notes:
            return "—"
        return obj.notes[:60] + "..." if len(obj.notes) > 60 else obj.notes

    notes_short.short_description = "الملاحظات"

    def has_add_permission(self, request):
        return False


