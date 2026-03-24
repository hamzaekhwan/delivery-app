"""
Payments Models - Payment tracking and transaction management
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel
from core.constants import PaymentMethod, PaymentStatus


class Payment(BaseModel):
    """
    Payment model - tracks payment for orders
    """
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name="الطلب"
    )
    
    # Payment details
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name="طريقة الدفع"
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="حالة الدفع"
    )
    
    # Amounts
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="المبلغ"
    )
    currency = models.CharField(
        max_length=3,
        default='SYP',
        verbose_name="العملة"
    )
    
    # Transaction details (for card/wallet payments)
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="معرف المعاملة"
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="استجابة البوابة"
    )
    
    # Timestamps
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الدفع"
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الفشل"
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الاسترداد"
    )
    
    # Refund details
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="مبلغ الاسترداد"
    )
    refund_reason = models.TextField(
        blank=True,
        verbose_name="سبب الاسترداد"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )

    class Meta:
        verbose_name = "دفعة"
        verbose_name_plural = "المدفوعات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
            models.Index(fields=['method', 'status']),
        ]

    def __str__(self):
        return f"Payment for Order #{self.order.order_number}"

    def mark_as_paid(self, transaction_id=None, gateway_response=None):
        """Mark payment as paid"""
        self.status = PaymentStatus.PAID
        self.paid_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
        
        # Update order payment status
        self.order.payment_status = PaymentStatus.PAID
        self.order.save(update_fields=['payment_status'])

    def mark_as_failed(self, reason=None, gateway_response=None):
        """Mark payment as failed"""
        self.status = PaymentStatus.FAILED
        self.failed_at = timezone.now()
        if reason:
            self.notes = reason
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
        
        # Update order payment status
        self.order.payment_status = PaymentStatus.FAILED
        self.order.save(update_fields=['payment_status'])

    def refund(self, amount=None, reason=None):
        """Process refund"""
        if self.status != PaymentStatus.PAID:
            return False, "لا يمكن استرداد دفعة غير مدفوعة"
        
        refund_amount = amount or self.amount
        if refund_amount > self.amount:
            return False, "مبلغ الاسترداد أكبر من مبلغ الدفعة"
        
        self.status = PaymentStatus.REFUNDED
        self.refunded_at = timezone.now()
        self.refund_amount = refund_amount
        if reason:
            self.refund_reason = reason
        self.save()
        
        # Update order payment status
        self.order.payment_status = PaymentStatus.REFUNDED
        self.order.save(update_fields=['payment_status'])
        
        return True, None


class PaymentTransaction(BaseModel):
    """
    Track all payment transactions (attempts, successful, failed)
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="الدفعة"
    )
    
    # Transaction type
    class TransactionType(models.TextChoices):
        PAYMENT = 'payment', 'دفع'
        REFUND = 'refund', 'استرداد'
        VERIFICATION = 'verification', 'تحقق'
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.PAYMENT,
        verbose_name="نوع المعاملة"
    )
    
    # Status
    is_successful = models.BooleanField(
        default=False,
        verbose_name="ناجحة"
    )
    
    # Amount
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="المبلغ"
    )
    
    # Gateway details
    gateway = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="البوابة"
    )
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="معرف المعاملة في البوابة"
    )
    gateway_response = models.JSONField(
        default=dict,
        verbose_name="استجابة البوابة"
    )
    
    # Error details
    error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="رمز الخطأ"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="رسالة الخطأ"
    )
    
    # IP and device info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="عنوان IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )

    class Meta:
        verbose_name = "معاملة دفع"
        verbose_name_plural = "معاملات الدفع"
        ordering = ['-created_at']

    def __str__(self):
        return f"Transaction {self.id} for Payment {self.payment.id}"


class Wallet(BaseModel):
    """
    User wallet for cashless payments
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name="المستخدم"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="الرصيد"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط"
    )

    class Meta:
        verbose_name = "محفظة"
        verbose_name_plural = "المحافظ"

    def __str__(self):
        return f"Wallet - {self.user.full_name}"

    def add_funds(self, amount, reason=''):
        """Add funds to wallet"""
        if amount <= 0:
            return False, "المبلغ يجب أن يكون أكبر من صفر"
        
        self.balance += Decimal(str(amount))
        self.save(update_fields=['balance'])
        
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=WalletTransaction.TransactionType.CREDIT,
            amount=amount,
            balance_after=self.balance,
            description=reason or "إضافة رصيد"
        )
        
        return True, None

    def deduct_funds(self, amount, reason=''):
        """Deduct funds from wallet"""
        if amount <= 0:
            return False, "المبلغ يجب أن يكون أكبر من صفر"
        
        if self.balance < amount:
            return False, "الرصيد غير كافي"
        
        self.balance -= Decimal(str(amount))
        self.save(update_fields=['balance'])
        
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type=WalletTransaction.TransactionType.DEBIT,
            amount=amount,
            balance_after=self.balance,
            description=reason or "خصم رصيد"
        )
        
        return True, None


class WalletTransaction(BaseModel):
    """
    Track wallet transactions
    """
    class TransactionType(models.TextChoices):
        CREDIT = 'credit', 'إضافة'
        DEBIT = 'debit', 'خصم'
        REFUND = 'refund', 'استرداد'
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="المحفظة"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="نوع المعاملة"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="المبلغ"
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="الرصيد بعد"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="الوصف"
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
        verbose_name="الطلب"
    )

    class Meta:
        verbose_name = "معاملة محفظة"
        verbose_name_plural = "معاملات المحفظة"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"
