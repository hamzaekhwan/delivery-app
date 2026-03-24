"""
Cart Models - Shopping cart system with multiple carts support
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from core.models import BaseModel
from core.utils import round_decimal, create_snapshot


# ═══════════════════════════════════════════════════════════
#                    Cart Settings
# ═══════════════════════════════════════════════════════════
CART_MAX_PER_USER = getattr(settings, "CART_MAX_PER_USER", 5)
CART_EXPIRY_HOURS = getattr(settings, "CART_EXPIRY_HOURS", 48)


# ═══════════════════════════════════════════════════════════
#                    Cart Manager
# ═══════════════════════════════════════════════════════════
class CartManager(models.Manager):
    """
    Custom manager for Cart with built-in filtering
    """

    def active(self):
        """Get only non-expired carts with items"""
        return self.filter(expires_at__gt=timezone.now()).exclude(items__isnull=True)

    def for_user(self, user):
        """Get all active carts for a user"""
        return self.active().filter(user=user).order_by("-updated_at")

    def cleanup_expired(self, user):
        """
        Delete expired and empty carts for user (Lazy Cleanup)
        Called before fetching carts
        """
        # Delete expired carts
        self.filter(user=user, expires_at__lt=timezone.now()).delete()

        # Delete empty carts (no items)
        self.filter(user=user).annotate(items_count_db=models.Count("items")).filter(
            items_count_db=0
        ).delete()


# ═══════════════════════════════════════════════════════════
#                    Cart Model
# ═══════════════════════════════════════════════════════════
class Cart(BaseModel):
    """
    Shopping cart - multiple carts per user allowed
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="المستخدم",
    )
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="المطعم",
    )

    # Expiration
    expires_at = models.DateTimeField(
        verbose_name="تنتهي في", db_index=True, blank=True, null=True
    )

    # Coupon
    coupon = models.ForeignKey(
        "coupons.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name="الكوبون",
    )

    # Special instructions
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # Custom Manager
    objects = CartManager()

    class Meta:
        verbose_name = "سلة"
        verbose_name_plural = "السلات"
        ordering = ["-updated_at"]
        # لا يوجد unique_together - يسمح بسلات متعددة

    def __str__(self):
        return f"Cart #{self.id} - {self.user.phone_number} - {self.restaurant.name}"

    def save(self, *args, **kwargs):
        # Set expiry on creation
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(hours=CART_EXPIRY_HOURS)
        super().save(*args, **kwargs)

    # ─────────────────────────────────────────────────────
    #                    Properties
    # ─────────────────────────────────────────────────────
    @property
    def is_expired(self):
        """Check if cart is expired"""
        return timezone.now() > self.expires_at

    @property
    def is_active(self):
        """Check if cart is active (not expired and has items)"""
        return not self.is_expired and self.items.exists()

    @property
    def time_remaining(self):
        """Get remaining time before expiry"""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()

    @property
    def items_count(self):
        """Total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        """Calculate subtotal (items total)"""
        total = sum(item.total_price for item in self.items.all())
        return round_decimal(total)

    @property
    def delivery_fee(self):
        """Calculate delivery fee based on user's current address distance"""
        from addresses.models import Address
        from core.utils import calculate_delivery_fee_between

        address = Address.objects.filter(user=self.user, is_current=True).first()

        if (
            address
            and address.latitude
            and address.longitude
            and self.restaurant.latitude
            and self.restaurant.longitude
        ):
            fee, _ = calculate_delivery_fee_between(
                float(address.latitude),
                float(address.longitude),
                float(self.restaurant.latitude),
                float(self.restaurant.longitude),
            )
            if fee is not None:
                return fee

        # Fallback to restaurant's static delivery fee (rounded up to nearest 1000)
        import math
        from decimal import Decimal

        return Decimal(
            str(math.ceil(float(self.restaurant.delivery_fee) / 1000) * 1000)
        )

    @property
    def discount_amount(self):
        if not self.coupon or not self.coupon.is_valid:
            return Decimal("0")

        can_use, _ = self.coupon.can_be_used_by(self.user, self.restaurant)
        if not can_use:
            return Decimal("0")

        return self.coupon.calculate_discount(
            self.subtotal, self.delivery_fee
        )  # ← أضف delivery_fee

    @property
    def total(self):
        """Calculate total (subtotal + delivery - discount)"""
        total = self.subtotal + self.delivery_fee - self.discount_amount
        return max(round_decimal(total), Decimal("0"))

    # ─────────────────────────────────────────────────────
    #                    Methods
    # ─────────────────────────────────────────────────────
    def refresh_expiry(self):
        """Refresh cart expiry time (call on any activity)"""
        self.expires_at = timezone.now() + timedelta(hours=CART_EXPIRY_HOURS)
        self.save(update_fields=["expires_at", "updated_at"])

    def get_price_breakdown(self):
        """Get detailed price breakdown"""
        return {
            "subtotal": str(self.subtotal),
            "delivery_fee": str(self.delivery_fee),
            "discount_amount": str(self.discount_amount),
            "coupon_code": self.coupon.code if self.coupon else None,
            "total": str(self.total),
            "items_count": self.items_count,
        }

    def apply_coupon(self, coupon):
        """Apply a coupon to the cart"""
        can_use, error = coupon.can_be_used_by(self.user, self.restaurant)
        if not can_use:
            raise ValueError(error)

        if self.subtotal < coupon.minimum_order_amount:
            raise ValueError(f"الحد الأدنى للطلب هو {coupon.minimum_order_amount}")

        self.coupon = coupon
        self.save(update_fields=["coupon"])
        return True

    def remove_coupon(self):
        """Remove coupon from cart"""
        self.coupon = None
        self.save(update_fields=["coupon"])

    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
        self.coupon = None
        self.save(update_fields=["coupon"])

    def create_snapshot(self):
        """Create a snapshot of cart for order"""
        items_snapshot = []
        for item in self.items.select_related("product", "variation").prefetch_related(
            "cart_item_addons"
        ):
            item_data = {
                "product_id": item.product.id,
                "product_name": item.product.name,
                "product_image": item.product.image.url if item.product.image else None,
                "base_price": str(item.product.base_price),
                "current_price": str(item.product.current_price),
                "quantity": item.quantity,
                "variation": None,
                "addons": [],
                "special_instructions": item.special_instructions,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }

            if item.variation:
                item_data["variation"] = {
                    "id": item.variation.id,
                    "name": item.variation.name,
                    "price_adjustment": str(item.variation.price_adjustment),
                }

            for addon in item.cart_item_addons.all():
                item_data["addons"].append(
                    {
                        "id": addon.addon.id,
                        "name": addon.addon.name,
                        "price": str(addon.addon.price),
                        "quantity": addon.quantity,
                    }
                )

            items_snapshot.append(item_data)

        return create_snapshot(
            {
                "restaurant_id": self.restaurant.id,
                "restaurant_name": self.restaurant.name,
                "items": items_snapshot,
                "subtotal": str(self.subtotal),
                "delivery_fee": str(self.delivery_fee),
                "discount_amount": str(self.discount_amount),
                "coupon_code": self.coupon.code if self.coupon else None,
                "total": str(self.total),
                "notes": self.notes,
            }
        )

    def validate_for_checkout(self, skip_restaurant_hours=False):
        """
        Validate cart is ready for checkout.
        Returns (is_valid, errors)
        skip_restaurant_hours=True للطلبات المجدولة — يتجاوز check الفتح/الإغلاق
        """
        errors = []

        # Check expiry
        if self.is_expired:
            errors.append("السلة منتهية الصلاحية")
            return False, errors

        # Check items
        if not self.items.exists():
            errors.append("السلة فارغة")
            return False, errors

        # Check restaurant
        if not self.restaurant.is_active:
            errors.append("المطعم غير متاح حالياً")

        if not skip_restaurant_hours and not self.restaurant.is_currently_open:
            errors.append("المطعم مغلق حالياً")

        # Check minimum order
        if self.subtotal < self.restaurant.minimum_order_amount:
            errors.append(
                f"الحد الأدنى للطلب هو {self.restaurant.minimum_order_amount}"
            )

        # Check items availability
        for item in self.items.select_related("product", "variation"):
            if not item.product.is_available:
                errors.append(f"{item.product.name} غير متوفر حالياً")

            if item.variation and not item.variation.is_available:
                errors.append(f"{item.variation.name} غير متوفر حالياً")

        return len(errors) == 0, errors

    @classmethod
    def get_user_cart_count(cls, user):
        """Get count of active carts for user"""
        return cls.objects.for_user(user).count()

    @classmethod
    def can_create_cart(cls, user):
        """Check if user can create a new cart"""
        return cls.get_user_cart_count(user) < CART_MAX_PER_USER


# ═══════════════════════════════════════════════════════════
#                    CartItem Model
# ═══════════════════════════════════════════════════════════
class CartItem(BaseModel):
    """
    Cart item
    """

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="السلة"
    )
    product = models.ForeignKey(
        "menu.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="المنتج",
    )
    variation = models.ForeignKey(
        "menu.ProductVariation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
        verbose_name="التنويع",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")
    special_instructions = models.TextField(blank=True, verbose_name="تعليمات خاصة")

    # Price snapshot (saved when item is added)
    price_snapshot = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="سعر الوحدة المحفوظ"
    )

    class Meta:
        verbose_name = "عنصر سلة"
        verbose_name_plural = "عناصر السلة"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        # Save price snapshot when creating
        if not self.pk:
            self.price_snapshot = self.calculate_unit_price()
        super().save(*args, **kwargs)

        # Refresh cart expiry on any item change
        self.cart.refresh_expiry()

    def delete(self, *args, **kwargs):
        cart = self.cart
        super().delete(*args, **kwargs)
        # Note: Empty cart cleanup happens via lazy cleanup

    def calculate_unit_price(self):
        """Calculate unit price including variation"""
        price = self.product.current_price
        if self.variation:
            price += self.variation.price_adjustment
        return price

    @property
    def unit_price(self):
        """Get unit price from snapshot"""
        return self.price_snapshot

    @property
    def addons_total(self):
        """Calculate total addons price"""
        return sum(
            addon.addon.price * addon.quantity for addon in self.cart_item_addons.all()
        )

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return round_decimal((self.unit_price + self.addons_total) * self.quantity)

    def update_quantity(self, quantity):
        """Update item quantity"""
        if quantity <= 0:
            self.delete()
            return None
        self.quantity = quantity
        self.save(update_fields=["quantity"])
        return self


# ═══════════════════════════════════════════════════════════
#                    CartItemAddon Model
# ═══════════════════════════════════════════════════════════
class CartItemAddon(BaseModel):
    """
    Addon for cart item
    """

    cart_item = models.ForeignKey(
        CartItem,
        on_delete=models.CASCADE,
        related_name="cart_item_addons",
        verbose_name="عنصر السلة",
    )
    addon = models.ForeignKey(
        "menu.ProductAddon",
        on_delete=models.CASCADE,
        related_name="cart_item_addons",
        verbose_name="الإضافة",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")

    class Meta:
        verbose_name = "إضافة عنصر سلة"
        verbose_name_plural = "إضافات عناصر السلة"
        unique_together = ["cart_item", "addon"]

    def __str__(self):
        return f"{self.addon.name} x {self.quantity}"

    @property
    def total_price(self):
        """Calculate total price for this addon"""
        return self.addon.price * self.quantity
