"""
Payments Serializers
"""

from decimal import Decimal
from rest_framework import serializers
from .models import Payment, PaymentTransaction, Wallet, WalletTransaction


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""

    order_number = serializers.CharField(source="order.order_number", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "order_number",
            "method",
            "method_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "transaction_id",
            "paid_at",
            "failed_at",
            "refunded_at",
            "refund_amount",
            "refund_reason",
            "created_at",
        ]
        read_only_fields = ["transaction_id", "paid_at", "failed_at", "refunded_at"]


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Detailed payment serializer with transactions"""

    order_number = serializers.CharField(source="order.order_number", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    transactions = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "order_number",
            "method",
            "method_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "transaction_id",
            "gateway_response",
            "paid_at",
            "failed_at",
            "refunded_at",
            "refund_amount",
            "refund_reason",
            "notes",
            "transactions",
            "created_at",
            "updated_at",
        ]

    def get_transactions(self, obj):
        transactions = obj.transactions.all()[:10]
        return PaymentTransactionSerializer(transactions, many=True).data


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Payment transaction serializer"""

    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "payment",
            "transaction_type",
            "transaction_type_display",
            "is_successful",
            "amount",
            "gateway",
            "gateway_transaction_id",
            "error_code",
            "error_message",
            "created_at",
        ]


class WalletSerializer(serializers.ModelSerializer):
    """Wallet serializer"""

    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user", "user_name", "balance", "is_active", "created_at"]
        read_only_fields = ["balance"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Wallet transaction serializer"""

    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )
    order_number = serializers.CharField(
        source="order.order_number", read_only=True, allow_null=True
    )

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "wallet",
            "transaction_type",
            "transaction_type_display",
            "amount",
            "balance_after",
            "description",
            "order",
            "order_number",
            "created_at",
        ]


class AddFundsSerializer(serializers.Serializer):
    """Serializer for adding funds to wallet"""

    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    payment_method = serializers.CharField(max_length=50)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("المبلغ يجب أن يكون أكبر من صفر")
        return value
