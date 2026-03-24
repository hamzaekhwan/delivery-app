"""
Coupon URLs
"""

from django.urls import path
from .views import ValidateCouponView, AvailableCouponsView

urlpatterns = [
    path("validate/", ValidateCouponView.as_view(), name="coupon-validate"),
    path("available/", AvailableCouponsView.as_view(), name="coupon-available"),
]
