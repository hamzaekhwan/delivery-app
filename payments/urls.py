"""
Payments URL Configuration
"""

from django.urls import path
from .views import (
    PaymentDetailView, OrderPaymentView, WalletView,
    WalletTransactionsView, AddFundsView, PaymentHistoryView,
    RetryPaymentView
)

app_name = 'payments'

urlpatterns = [
    # Payments
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('order/<int:order_id>/', OrderPaymentView.as_view(), name='order-payment'),
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('<int:payment_id>/retry/', RetryPaymentView.as_view(), name='retry-payment'),
    
    # Wallet
    path('wallet/', WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', WalletTransactionsView.as_view(), name='wallet-transactions'),
    path('wallet/add-funds/', AddFundsView.as_view(), name='add-funds'),
]
