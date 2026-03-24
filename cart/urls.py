"""
Cart URL Configuration - Updated for multiple carts support
"""

from django.urls import path
from .views import (
    CartListView,
    CartView,
    AddToCartView,
    UpdateCartItemView,
    ClearCartView,
    ClearCartItemsView,
    ApplyCouponView,
    ValidateCartView,
    SelectCartView,
)

app_name = "cart"

urlpatterns = [
    # ═══════════════════════════════════════════════════════════
    #                    Cart Operations
    # ═══════════════════════════════════════════════════════════
    # List all carts
    # GET /cart/all/
    path("all/", CartListView.as_view(), name="cart-list"),
    # Get single cart (by cart_id or restaurant_id query param)
    # GET /cart/?cart_id=1 or GET /cart/?restaurant_id=1
    path("", CartView.as_view(), name="cart-detail"),
    # Add item to cart
    # POST /cart/add/
    path("add/", AddToCartView.as_view(), name="add-to-cart"),
    # Update/Delete cart item
    # PATCH /cart/item/1/
    # DELETE /cart/item/1/
    path("item/<int:item_id>/", UpdateCartItemView.as_view(), name="update-item"),
    # ═══════════════════════════════════════════════════════════
    #                    Cart Management
    # ═══════════════════════════════════════════════════════════
    # Delete entire cart
    # DELETE /cart/delete/?cart_id=1
    path("delete/", ClearCartView.as_view(), name="delete-cart"),
    # Clear cart items only
    # DELETE /cart/1/clear/
    path("<int:cart_id>/clear/", ClearCartItemsView.as_view(), name="clear-cart-items"),
    # ═══════════════════════════════════════════════════════════
    #                    Checkout Flow
    # ═══════════════════════════════════════════════════════════
    # Validate cart
    # GET /cart/validate/?cart_id=1
    path("validate/", ValidateCartView.as_view(), name="validate-cart"),
    # Select cart for checkout
    # # POST /cart/1/select/
    # path('<int:cart_id>/select/', SelectCartView.as_view(), name='select-cart'),
    # ═══════════════════════════════════════════════════════════
    #                    Coupon Operations
    # ═══════════════════════════════════════════════════════════
    # Apply/Remove coupon
    # POST /cart/1/coupon/
    # DELETE /cart/1/coupon/
    path("<int:cart_id>/coupon/", ApplyCouponView.as_view(), name="apply-coupon"),
]
