"""
Payments Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, PaymentTransaction, Wallet, WalletTransaction


class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0
    readonly_fields = [
        'transaction_type', 'is_successful', 'amount', 'gateway',
        'gateway_transaction_id', 'error_code', 'error_message',
        'ip_address', 'created_at'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'order_link', 'method', 'amount', 'currency',
        'status_badge', 'paid_at', 'created_at'
    ]
    list_filter = ['method', 'status', 'currency', 'created_at']
    search_fields = [
        'order__order_number', 'transaction_id',
        'order__user__phone_number'
    ]
    readonly_fields = [
        'order', 'method', 'amount', 'currency', 'transaction_id',
        'gateway_response', 'paid_at', 'failed_at', 'refunded_at',
        'created_at', 'updated_at'
    ]
    inlines = [PaymentTransactionInline]
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order',)
        }),
        ('Payment Details', {
            'fields': ('method', 'status', 'amount', 'currency')
        }),
        ('Transaction', {
            'fields': ('transaction_id', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Refund', {
            'fields': ('refund_amount', 'refund_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('paid_at', 'failed_at', 'refunded_at', 'created_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_failed']
    
    def order_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.order.order_number
        )
    order_link.short_description = "Order"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'failed': '#dc3545',
            'refunded': '#6c757d',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    @admin.action(description="Mark as Paid")
    def mark_as_paid(self, request, queryset):
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_as_paid()
            count += 1
        self.message_user(request, f"{count} payments marked as paid.")
    
    @admin.action(description="Mark as Failed")
    def mark_as_failed(self, request, queryset):
        count = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_as_failed(reason="Marked as failed by admin")
            count += 1
        self.message_user(request, f"{count} payments marked as failed.")
    
    def has_add_permission(self, request):
        return False


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment', 'transaction_type', 'amount',
        'is_successful', 'gateway', 'created_at'
    ]
    list_filter = ['transaction_type', 'is_successful', 'gateway', 'created_at']
    search_fields = ['payment__order__order_number', 'gateway_transaction_id']
    readonly_fields = [
        'payment', 'transaction_type', 'is_successful', 'amount',
        'gateway', 'gateway_transaction_id', 'gateway_response',
        'error_code', 'error_message', 'ip_address', 'user_agent',
        'created_at'
    ]
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = [
        'transaction_type', 'amount', 'balance_after',
        'description', 'order', 'created_at'
    ]
    can_delete = False
    ordering = ['-created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'balance', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['user', 'balance', 'created_at', 'updated_at']
    inlines = [WalletTransactionInline]
    list_per_page = 50
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Balance', {
            'fields': ('balance', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['add_funds_100', 'add_funds_500', 'deactivate_wallets']
    
    @admin.action(description="Add 100 to balance")
    def add_funds_100(self, request, queryset):
        for wallet in queryset:
            wallet.add_funds(100, "Admin added funds")
        self.message_user(request, f"Added 100 to {queryset.count()} wallets.")
    
    @admin.action(description="Add 500 to balance")
    def add_funds_500(self, request, queryset):
        for wallet in queryset:
            wallet.add_funds(500, "Admin added funds")
        self.message_user(request, f"Added 500 to {queryset.count()} wallets.")
    
    @admin.action(description="Deactivate wallets")
    def deactivate_wallets(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} wallets deactivated.")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'wallet', 'transaction_type', 'amount',
        'balance_after', 'description', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = [
        'wallet__user__phone_number', 'wallet__user__full_name',
        'description'
    ]
    readonly_fields = [
        'wallet', 'transaction_type', 'amount', 'balance_after',
        'description', 'order', 'created_at'
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
