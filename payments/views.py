"""
Payments Views
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from .models import Payment, Wallet, WalletTransaction
from .serializers import (
    PaymentSerializer, PaymentDetailSerializer,
    WalletSerializer, WalletTransactionSerializer,
    AddFundsSerializer
)


class PaymentDetailView(generics.RetrieveAPIView):
    """
    Get payment details
    """
    serializer_class = PaymentDetailSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Get payment details"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return Payment.objects.filter(order__user=self.request.user)


class OrderPaymentView(APIView):
    """
    Get payment for a specific order
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Get order payment",
        responses={200: PaymentDetailSerializer}
    )
    def get(self, request, order_id):
        payment = get_object_or_404(
            Payment,
            order_id=order_id,
            order__user=request.user
        )
        serializer = PaymentDetailSerializer(payment)
        return Response(serializer.data)


class WalletView(APIView):
    """
    Get user's wallet
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Get wallet",
        responses={200: WalletSerializer}
    )
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class WalletTransactionsView(generics.ListAPIView):
    """
    Get wallet transaction history
    """
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Get wallet transactions"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        wallet = get_object_or_404(Wallet, user=self.request.user)
        return WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:50]


class AddFundsView(APIView):
    """
    Add funds to wallet (placeholder for payment gateway integration)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Add funds to wallet",
        request=AddFundsSerializer,
        responses={200: WalletSerializer}
    )
    def post(self, request):
        serializer = AddFundsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        if not wallet.is_active:
            return Response(
                {'error': 'Wallet is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount = serializer.validated_data['amount']
        
        # In production, integrate with payment gateway here
        # For now, directly add funds
        success, error = wallet.add_funds(amount, "Wallet top-up")
        
        if not success:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(WalletSerializer(wallet).data)


class PaymentHistoryView(generics.ListAPIView):
    """
    Get user's payment history
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Get payment history"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        return Payment.objects.filter(
            order__user=self.request.user
        ).select_related('order').order_by('-created_at')[:50]


class RetryPaymentView(APIView):
    """
    Retry a failed payment
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Payments'],
        summary="Retry payment"
    )
    def post(self, request, payment_id):
        payment = get_object_or_404(
            Payment,
            pk=payment_id,
            order__user=request.user
        )
        
        if payment.status != 'failed':
            return Response(
                {'error': 'Only failed payments can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if order is still valid
        if payment.order.status == 'cancelled':
            return Response(
                {'error': 'Order has been cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In production, initiate payment with gateway
        # For now, return a payment URL or status
        
        return Response({
            'status': 'payment_retry_initiated',
            'payment_id': payment.id,
            'amount': str(payment.amount),
            'method': payment.method
        })
