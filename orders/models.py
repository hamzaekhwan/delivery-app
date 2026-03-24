"""
Orders Models - Complete order lifecycle management
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from core.models import BaseModel
from core.constants import (
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    DriverOrderAction,
    ORDER_STATUS_TRANSITIONS,
)
from core.utils import generate_order_number, round_decimal
from django.db import transaction


class Order(BaseModel):
    """
    Main Order model with complete snapshot for historical accuracy
    """

    # Order identifiers
    order_number = models.CharField(
        max_length=50, unique=True, verbose_name="رقم الطلب"
    )

    # User and Restaurant
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        verbose_name="المستخدم",
        null=True,
        blank=True,
    )
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="المطعم",
        null=True,
        blank=True,
    )

    # Driver
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driver_orders",
        verbose_name="السائق",
        limit_choices_to={"role": "driver"},
    )

    # Delivery Address
    delivery_address = models.ForeignKey(
        "addresses.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="عنوان التوصيل",
    )

    # Order Status
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        verbose_name="الحالة",
    )

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        verbose_name="طريقة الدفع",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="حالة الدفع",
    )

    # Coupon
    coupon = models.ForeignKey(
        "coupons.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="الكوبون",
    )

    # Pricing
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="المجموع الفرعي"
    )
    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="رسوم التوصيل"
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="قيمة الخصم"
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الإجمالي"
    )
    restaurant_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="المبلغ المستحق للمطعم",
        help_text="المبلغ الذي سيتم دفعه للمطعم بعد خصم نسبة التطبيق",
    )
    app_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="نسبة تخفيض التطبيق",
    )

    # Pending Price (for manual orders where price is unknown at creation)
    is_price_pending = models.BooleanField(
        default=False,
        verbose_name="السعر غير محدد",
        help_text="الدرايفر سيدخل السعر عند الاستلام من المحل",
    )
    final_price_set_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت تحديد السعر النهائي",
    )

    # Snapshots (JSON)
    restaurant_snapshot = models.JSONField(default=dict, verbose_name="بيانات المطعم")
    address_snapshot = models.JSONField(default=dict, verbose_name="بيانات العنوان")
    items_snapshot = models.JSONField(default=list, verbose_name="بيانات المنتجات")

    # Notes
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    special_instructions = models.TextField(blank=True, verbose_name="تعليمات خاصة")

    # Manual order (admin-created)
    is_manual = models.BooleanField(default=False, verbose_name="طلب يدوي")
    chat_order_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="معرف طلب الشات",
        help_text="معرف الطلب من محادثة الشات في التطبيق",
    )
    description = models.TextField(blank=True, verbose_name="وصف الطلب")
    delivery_address_text = models.TextField(
        blank=True, verbose_name="عنوان التوصيل (نص)"
    )
    restaurant_name_manual = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="اسم المطعم (يدوي)",
        help_text="للطلبات اليدوية التي لا ترتبط بمطعم مسجل",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_orders",
        verbose_name="أنشئ بواسطة",
        help_text="الأدمن الذي أنشأ الطلب اليدوي",
    )

    # Contact & Scheduling
    contact_phone = models.CharField(
        max_length=20, blank=True, verbose_name="رقم التواصل"
    )
    scheduled_delivery_time = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت التوصيل المطلوب"
    )
    is_scheduled = models.BooleanField(default=False, verbose_name="طلب مجدول")

    # Timestamps for tracking
    placed_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الطلب")
    confirmed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت التأكيد"
    )
    preparing_at = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت بدء التحضير"
    )
    picked_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الاستلام")
    delivered_at = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت التوصيل"
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت الإلغاء"
    )

    # Cancellation
    cancellation_reason = models.TextField(blank=True, verbose_name="سبب الإلغاء")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_orders",
        verbose_name="ملغي بواسطة",
    )

    # Estimated delivery
    estimated_delivery_time = models.DateTimeField(
        null=True, blank=True, verbose_name="وقت التوصيل المتوقع"
    )

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["driver", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    def can_transition_to(self, new_status):
        """Check if order can transition to the given status"""
        allowed = ORDER_STATUS_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def update_status(self, new_status, user=None, reason=None, force=False):
        """
        Update order status with validation and history tracking.
        Returns (success, error_message)
        force=True يتجاوز قيود الانتقال (للأدمن)
        """
        # Business logic validation for CONFIRMED status
        if not force and new_status == OrderStatus.CONFIRMED and not self.is_scheduled:
            return False, "لا يمكن تأكيد طلب غير مجدول"

        if not force and not self.can_transition_to(new_status):
            return (
                False,
                f"لا يمكن الانتقال من {self.get_status_display()} إلى {OrderStatus(new_status).label}",
            )

        old_status = self.status
        self.status = new_status

        # Update corresponding timestamp
        now = timezone.now()
        timestamp_map = {
            OrderStatus.PLACED: "placed_at",
            OrderStatus.CONFIRMED: "confirmed_at",
            OrderStatus.PREPARING: "preparing_at",
            OrderStatus.PICKED: "picked_at",
            OrderStatus.DELIVERED: "delivered_at",
            OrderStatus.CANCELLED: "cancelled_at",
        }

        if new_status in timestamp_map:
            setattr(self, timestamp_map[new_status], now)

        # Handle cancellation
        if new_status == OrderStatus.CANCELLED:
            self.cancelled_by = user
            self.cancellation_reason = reason or ""
            self.driver = None

        self.save()

        # Expire pending driver requests when order leaves PREPARING
        if new_status in (OrderStatus.CANCELLED, OrderStatus.PICKED, OrderStatus.DELIVERED):
            self.driver_requests.filter(
                action=DriverOrderAction.PENDING
            ).update(action=DriverOrderAction.EXPIRED, responded_at=now)

        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            notes=reason or "",
        )

        return True, None

    @classmethod
    def create_from_cart(
        cls,
        cart,
        delivery_address,
        payment_method=PaymentMethod.CASH,
        notes="",
        contact_phone="",
        scheduled_delivery_time=None,
        is_scheduled=False,
    ):
        """
        Create an order from a cart.
        يحسب الخصومات بشكل صحيح مع التفريق بين:
        - خصم المنتج/المطعم (للزبون)
        - عمولة التطبيق (للشركة)
        - الكوبون
        """
        # Validate cart — الطلبات المجدولة تتجاوز check ساعات العمل
        is_valid, errors = cart.validate_for_checkout(
            skip_restaurant_hours=is_scheduled
        )
        if not is_valid:
            raise ValueError(", ".join(errors))

        with transaction.atomic():
            # Create restaurant snapshot
            restaurant = cart.restaurant
            restaurant_snapshot = {
                "id": restaurant.id,
                "name": restaurant.name,
                "name_en": restaurant.name_en,
                "logo": restaurant.logo.url if restaurant.logo else None,
                "phone": restaurant.phone,
                "address": restaurant.address,
                "delivery_time_estimate": restaurant.delivery_time_estimate,
            }

            # Create address snapshot
            address_snapshot = {
                "id": delivery_address.id,
                "title": delivery_address.title,
                "governorate": delivery_address.governorate.name,
                "area": delivery_address.area.name,
                "street": delivery_address.street,
                "building_number": delivery_address.building_number,
                "floor": delivery_address.floor,
                "apartment": delivery_address.apartment,
                "landmark": delivery_address.landmark,
                "full_address": delivery_address.full_address,
                "latitude": str(delivery_address.latitude)
                if delivery_address.latitude
                else None,
                "longitude": str(delivery_address.longitude)
                if delivery_address.longitude
                else None,
            }

            # Create items snapshot
            items_snapshot = cart.create_snapshot()["items"]

            # ── subtotal (مجموع current_price × quantity — الخصم مدمج) ──
            subtotal = cart.subtotal

            # ── حساب خصم المنتج/المطعم الحقيقي ──
            # الفرق بين base_price و current_price لكل عنصر
            product_discount_amount = Decimal("0")
            for item in cart.items.select_related(
                "product", "variation"
            ).prefetch_related("cart_item_addons__addon"):
                base = item.product.base_price
                current = item.product.current_price
                if item.variation:
                    base += item.variation.price_adjustment
                    current += item.variation.price_adjustment

                addons_total = sum(
                    a.addon.price * a.quantity for a in item.cart_item_addons.all()
                )

                base_item_total = (base + addons_total) * item.quantity
                current_item_total = (current + addons_total) * item.quantity
                product_discount_amount += base_item_total - current_item_total

            product_discount_amount = max(
                round_decimal(product_discount_amount), Decimal("0")
            )

            # ── رسوم التوصيل ──
            import math

            delivery_fee = Decimal(
                str(math.ceil(float(cart.restaurant.delivery_fee) / 1000) * 1000)
            )  # fallback
            try:
                from core.utils import calculate_delivery_fee_between

                if (
                    delivery_address.latitude
                    and delivery_address.longitude
                    and restaurant.latitude
                    and restaurant.longitude
                ):
                    fee, _ = calculate_delivery_fee_between(
                        float(delivery_address.latitude),
                        float(delivery_address.longitude),
                        float(restaurant.latitude),
                        float(restaurant.longitude),
                    )
                    if fee is not None:
                        delivery_fee = fee
            except Exception:
                pass

            # ── خصم الكوبون (منفصل عن خصم المنتج/المطعم) ──
            coupon_discount = Decimal("0")
            if cart.coupon:
                coupon_discount = cart.coupon.calculate_discount(subtotal, delivery_fee)

            # ── إجمالي الخصم = خصم المنتج/المطعم + خصم الكوبون ──
            discount_amount = product_discount_amount + coupon_discount

            # ── إجمالي ما يدفعه الزبون ──
            # subtotal أصلاً مخفض، فنخصم الكوبون فقط
            total = subtotal + delivery_fee - coupon_discount
            total = max(round_decimal(total), Decimal("0"))

            # ── مستحقات المطعم — المنطق المصحح ──
            app_discount_pct = restaurant.app_discount_percentage or Decimal("0")

            # هل فيه خصم لصالح الزبون (المطعم يتحمله)؟
            has_customer_discount = (
                restaurant.has_discount and restaurant.current_discount
            ) or product_discount_amount > 0

            if has_customer_discount:
                # الخصم لصالح الزبون — المطعم يحصل على subtotal كاملاً
                # لأن الخصم أصلاً خرج من جيب المطعم عبر تخفيض السعر
                restaurant_total = round_decimal(subtotal)
            else:
                # عمولة للشركة — المطعم يحصل على subtotal ناقص العمولة
                if app_discount_pct > 0:
                    restaurant_total = subtotal - (
                        subtotal * app_discount_pct / Decimal("100")
                    )
                    restaurant_total = round_decimal(restaurant_total)
                else:
                    restaurant_total = round_decimal(subtotal)

            # Create order with retry for duplicate order_number
            from django.db import IntegrityError

            for attempt in range(5):
                try:
                    with transaction.atomic():
                        order = cls.objects.create(
                            user=cart.user,
                            restaurant=restaurant,
                            delivery_address=delivery_address,
                            payment_method=payment_method,
                            coupon=cart.coupon,
                            subtotal=subtotal,
                            delivery_fee=delivery_fee,
                            discount_amount=discount_amount,
                            total=total,
                            restaurant_total=restaurant_total,
                            app_discount_percentage=app_discount_pct,
                            restaurant_snapshot=restaurant_snapshot,
                            address_snapshot=address_snapshot,
                            items_snapshot=items_snapshot,
                            notes=notes,
                            contact_phone=contact_phone,
                            scheduled_delivery_time=scheduled_delivery_time,
                            is_scheduled=is_scheduled,
                            status=OrderStatus.DRAFT,
                        )
                    break
                except IntegrityError:
                    if attempt == 4:
                        raise

            # Create order items
            for item in cart.items.all():
                order_item = OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variation=item.variation,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    special_instructions=item.special_instructions,
                )

                # Copy addons
                for addon in item.cart_item_addons.all():
                    OrderItemAddon.objects.create(
                        order_item=order_item,
                        addon=addon.addon,
                        quantity=addon.quantity,
                        price=addon.addon.price,
                    )

            # Clear cart
            cart.clear()

            # تسجيل استخدام الكوبون
            if order.coupon:
                order.coupon.use(user=cart.user, order=order)

            return order

    def place_order(self):
        """Place the order (move from draft to placed)"""
        return self.update_status(OrderStatus.PLACED)

    @property
    def items_count(self):
        """Total number of items"""
        return sum(item.quantity for item in self.items.all())

    @property
    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in [
            OrderStatus.DRAFT,
            OrderStatus.PLACED,
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
        ]

    @property
    def can_review(self):
        """Check if order can be reviewed"""
        return self.status == OrderStatus.DELIVERED

    @property
    def is_active(self):
        """Check if order is still active"""
        return self.status not in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]

    def get_tracking_info(self):
        """Get order tracking information"""
        return {
            "order_number": self.order_number,
            "status": self.status,
            "status_display": self.get_status_display(),
            "placed_at": self.placed_at,
            "preparing_at": self.preparing_at,
            "picked_at": self.picked_at,
            "delivered_at": self.delivered_at,
            "estimated_delivery_time": self.estimated_delivery_time,
            "is_scheduled": self.is_scheduled,
            "scheduled_delivery_time": self.scheduled_delivery_time,
            "is_price_pending": self.is_price_pending,
            "driver": {
                "name": self.driver.full_name if self.driver else None,
                "phone": self.driver.phone_number if self.driver else None,
            }
            if self.driver
            else None,
        }


class OrderItem(BaseModel):
    """Order item with stored prices"""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="الطلب"
    )
    product = models.ForeignKey(
        "menu.Product",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name="المنتج",
    )
    variation = models.ForeignKey(
        "menu.ProductVariation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="التنويع",
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="سعر الوحدة"
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="الإجمالي"
    )
    special_instructions = models.TextField(blank=True, verbose_name="تعليمات خاصة")

    product_snapshot = models.JSONField(default=dict, verbose_name="بيانات المنتج")

    class Meta:
        verbose_name = "عنصر طلب"
        verbose_name_plural = "عناصر الطلب"
        ordering = ["created_at"]

    def __str__(self):
        product_name = self.product.name if self.product else "منتج محذوف"
        return f"{product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if not self.product_snapshot and self.product:
            self.product_snapshot = {
                "id": self.product.id,
                "name": self.product.name,
                "name_en": self.product.name_en,
                "image": self.product.image.url if self.product.image else None,
                "base_price": str(self.product.base_price),
            }

            if self.variation:
                self.product_snapshot["variation"] = {
                    "id": self.variation.id,
                    "name": self.variation.name,
                    "price_adjustment": str(self.variation.price_adjustment),
                }

        super().save(*args, **kwargs)


class OrderItemAddon(BaseModel):
    """Addon for order item"""

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="order_item_addons",
        verbose_name="عنصر الطلب",
    )
    addon = models.ForeignKey(
        "menu.ProductAddon",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_item_addons",
        verbose_name="الإضافة",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")

    class Meta:
        verbose_name = "إضافة عنصر طلب"
        verbose_name_plural = "إضافات عناصر الطلب"

    def __str__(self):
        addon_name = self.addon.name if self.addon else "إضافة محذوفة"
        return f"{addon_name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


class OrderStatusHistory(BaseModel):
    """Track all order status changes"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="الطلب",
    )
    from_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, verbose_name="من الحالة"
    )
    to_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, verbose_name="إلى الحالة"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تم بواسطة",
    )
    notes = models.TextField(blank=True, default="", verbose_name="ملاحظات")

    class Meta:
        verbose_name = "سجل حالة الطلب"
        verbose_name_plural = "سجل حالات الطلبات"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Order #{self.order.order_number}: {self.from_status} → {self.to_status}"
        )


class DriverOrderRequest(BaseModel):
    """Track order requests sent to drivers"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="driver_requests",
        verbose_name="الطلب",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="order_requests",
        verbose_name="السائق",
        limit_choices_to={"role": "driver"},
    )
    action = models.CharField(
        max_length=20,
        choices=DriverOrderAction.choices,
        default=DriverOrderAction.PENDING,
        verbose_name="الإجراء",
    )
    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="المسافة (كم)",
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الرد")
    rejection_reason = models.TextField(blank=True, verbose_name="سبب الرفض")

    class Meta:
        verbose_name = "طلب سائق"
        verbose_name_plural = "طلبات السائقين"
        ordering = ["-sent_at"]
        unique_together = ["order", "driver"]

    def __str__(self):
        return f"Order #{self.order.order_number} → {self.driver.full_name}"

    @property
    def is_expired(self):
        """منتهي فقط إذا سائق آخر أخذ الطلب"""
        return self.action == DriverOrderAction.EXPIRED

    def accept(self):
        """Accept the order request"""
        if self.action != DriverOrderAction.PENDING:
            return False, "تم الرد على هذا الطلب مسبقاً"

        if self.order.status != OrderStatus.PREPARING:
            return False, "هذا الطلب لم يعد متاحاً"

        if self.order.driver:
            return False, "تم تعيين سائق آخر لهذا الطلب"

        if not self.driver.is_online:
            return False, "يجب أن تكون متصلاً لقبول الطلبات"

        # لا يمكن قبول طلب جديد إذا عنده طلب نشط
        active_order = Order.objects.filter(
            driver=self.driver,
            status__in=[
                OrderStatus.CONFIRMED,
                OrderStatus.PREPARING,
                OrderStatus.PICKED,
            ],
        ).exists()
        if active_order:
            return False, "لديك طلب قيد التوصيل، أكمله أولاً"

        # لا يمكن قبول طلب جديد إذا ما أرسل تقرير تسليم للطلب السابق
        delivered_without_report = Order.objects.filter(
            driver=self.driver,
            status=OrderStatus.DELIVERED,
        ).exclude(
            delivery_report__isnull=False,
        ).exists()
        if delivered_without_report:
            return False, "يجب إرسال تقرير التسليم للطلب السابق أولاً"

        self.action = DriverOrderAction.ACCEPTED
        self.responded_at = timezone.now()
        self.save()

        self.order.driver = self.driver
        self.order.save(update_fields=["driver"])

        DriverOrderRequest.objects.filter(
            order=self.order, action=DriverOrderAction.PENDING
        ).exclude(id=self.id).update(
            action=DriverOrderAction.EXPIRED, responded_at=timezone.now()
        )

        return True, None

    def reject(self, reason=""):
        """Reject the order request"""
        if self.action != DriverOrderAction.PENDING:
            return False, "تم الرد على هذا الطلب مسبقاً"

        self.action = DriverOrderAction.REJECTED
        self.responded_at = timezone.now()
        self.rejection_reason = reason
        self.save()

        return True, None

    @classmethod
    def send_to_all_drivers(cls, order):
        """Send order request to all available drivers."""
        from accounts.models import User

        available_drivers = User.objects.filter(
            role=User.Role.DRIVER,
            is_active=True,
        )

        cls.objects.filter(order=order, action=DriverOrderAction.PENDING).update(
            action=DriverOrderAction.EXPIRED
        )

        requests = []
        for driver in available_drivers:
            try:
                request = cls.objects.create(order=order, driver=driver)
                requests.append(request)
            except Exception:
                continue

        return requests


class OrderDeliveryReport(BaseModel):
    """تقرير السائق بعد تسليم الطلب"""

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_report",
        verbose_name="الطلب",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="delivery_reports",
        verbose_name="السائق",
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات السائق")

    class Meta:
        verbose_name = "تقرير التسليم"
        verbose_name_plural = "تقارير التسليم"
        ordering = ["-created_at"]

    def __str__(self):
        return f"تقرير الطلب #{self.order.order_number}"


class OrderDeliveryReportImage(BaseModel):
    """صور تقرير التسليم"""

    report = models.ForeignKey(
        OrderDeliveryReport,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="التقرير",
    )
    image = models.ImageField(upload_to="delivery_reports/", verbose_name="الصورة")
    caption = models.CharField(max_length=200, blank=True, verbose_name="وصف الصورة")

    class Meta:
        verbose_name = "صورة تقرير"
        verbose_name_plural = "صور التقارير"
