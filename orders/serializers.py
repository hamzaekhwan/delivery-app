"""
Orders Serializers - Complete order API serialization
"""

from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from .models import (
    Order,
    OrderItem,
    OrderItemAddon,
    OrderStatusHistory,
    DriverOrderRequest,
    OrderDeliveryReport,
    OrderDeliveryReportImage,
)
from core.constants import OrderStatus, PaymentMethod
from coupons.models import Coupon


class OrderItemAddonSerializer(serializers.ModelSerializer):
    addon_name = serializers.CharField(source="addon.name", read_only=True)

    class Meta:
        model = OrderItemAddon
        fields = ["id", "addon", "addon_name", "quantity", "price", "total_price"]
        read_only_fields = ["price", "total_price"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.ImageField(source="product.image", read_only=True)
    variation_name = serializers.CharField(
        source="variation.name", read_only=True, allow_null=True
    )
    addons = OrderItemAddonSerializer(
        source="order_item_addons", many=True, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_image",
            "variation",
            "variation_name",
            "quantity",
            "unit_price",
            "total_price",
            "special_instructions",
            "product_snapshot",
            "addons",
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    from_status_display = serializers.CharField(
        source="get_from_status_display", read_only=True
    )
    to_status_display = serializers.CharField(
        source="get_to_status_display", read_only=True
    )
    changed_by_name = serializers.CharField(
        source="changed_by.full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = OrderStatusHistory
        fields = [
            "id",
            "from_status",
            "from_status_display",
            "to_status",
            "to_status_display",
            "changed_by",
            "changed_by_name",
            "notes",
            "created_at",
        ]


class OrderListSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source="restaurant.name", read_only=True, allow_null=True
    )
    restaurant_name_en = serializers.CharField(
        source="restaurant.name_en", read_only=True, allow_null=True
    )
    restaurant_logo = serializers.ImageField(
        source="restaurant.logo", read_only=True, allow_null=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "restaurant",
            "restaurant_name",
            "restaurant_name_en",
            "restaurant_logo",
            "total",
            "items_count",
            "payment_method",
            "payment_method_display",
            "is_scheduled",
            "scheduled_delivery_time",
            "created_at",
            "placed_at",
            "delivered_at",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    is_driver_rated = serializers.SerializerMethodField()
    restaurant_name = serializers.CharField(
        source="restaurant.name", read_only=True, allow_null=True
    )
    restaurant_logo = serializers.ImageField(
        source="restaurant.logo", read_only=True, allow_null=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    payment_status_display = serializers.CharField(
        source="get_payment_status_display", read_only=True
    )
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.CharField(
        source="driver.phone_number", read_only=True, allow_null=True
    )
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    tracking_info = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "restaurant",
            "restaurant_name",
            "restaurant_logo",
            "driver",
            "driver_name",
            "driver_phone",
            "payment_method",
            "payment_method_display",
            "payment_status",
            "payment_status_display",
            "subtotal",
            "delivery_fee",
            "discount_amount",
            "total",
            "restaurant_total",
            "coupon",
            "items_count",
            "can_cancel",
            "can_review",
            "is_price_pending",
            "final_price_set_at",
            "restaurant_snapshot",
            "address_snapshot",
            "items_snapshot",
            "notes",
            "special_instructions",
            "contact_phone",
            "is_scheduled",
            "scheduled_delivery_time",
            "placed_at",
            "confirmed_at",
            "preparing_at",
            "picked_at",
            "delivered_at",
            "is_driver_rated",
            "cancelled_at",
            "estimated_delivery_time",
            "cancellation_reason",
            "items",
            "status_history",
            "tracking_info",
            "created_at",
            "updated_at",
        ]

    def get_driver_name(self, obj):
        accepted_request = (
            DriverOrderRequest.objects.filter(order=obj, action="accepted")
            .select_related("driver__hero")
            .first()
        )
        if not accepted_request:
            return None
        driver = accepted_request.driver
        if driver.hero:
            return f"#{driver.hero.number}"
        return driver.full_name

    def get_is_driver_rated(self, obj):
        try:
            return obj.driver_review is not None
        except Exception:
            return False

    def get_tracking_info(self, obj):
        return obj.get_tracking_info()


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField(help_text="معرف السلة")
    delivery_address_id = serializers.IntegerField(help_text="معرف عنوان التوصيل")
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    scheduled_delivery_time = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_cart_id(self, value):
        from cart.models import Cart

        user = self.context["request"].user
        try:
            cart = Cart.objects.get(id=value, user=user)
            if not cart.items.exists():
                raise serializers.ValidationError("السلة فارغة")
        except Cart.DoesNotExist:
            raise serializers.ValidationError("السلة غير موجودة")
        return value

    def validate_delivery_address_id(self, value):
        from addresses.models import Address

        user = self.context["request"].user
        if not Address.objects.filter(id=value, user=user).exists():
            raise serializers.ValidationError("العنوان غير موجود")
        return value

    def validate_scheduled_delivery_time(self, value):
        if value:
            min_time = timezone.now() + timezone.timedelta(minutes=30)
            if value < min_time:
                raise serializers.ValidationError(
                    "وقت التوصيل يجب أن يكون بعد 30 دقيقة على الأقل"
                )
            max_time = timezone.now() + timezone.timedelta(days=7)
            if value > max_time:
                raise serializers.ValidationError("لا يمكن جدولة طلب لأكثر من 7 أيام")
        return value

    def validate_coupon_code(self, value):
        if not value:
            return None
        try:
            coupon = Coupon.objects.get(code=value)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("الكوبون غير موجود")
        can_use, error = coupon.can_be_used_by(self.context["request"].user)
        if not can_use:
            raise serializers.ValidationError(error)
        return coupon

    def create(self, validated_data):
        from addresses.models import Address
        from cart.models import Cart

        user = self.context["request"].user
        cart = Cart.objects.get(id=validated_data["cart_id"], user=user)
        address = Address.objects.get(id=validated_data["delivery_address_id"])

        coupon = validated_data.get("coupon_code")
        if coupon:
            cart.coupon = coupon
            cart.save(update_fields=["coupon"])

        contact_phone = validated_data.get("contact_phone") or user.phone_number
        scheduled_time = validated_data.get("scheduled_delivery_time")

        try:
            order = Order.create_from_cart(
                cart=cart,
                delivery_address=address,
                payment_method=validated_data["payment_method"],
                notes=validated_data.get("notes", ""),
                contact_phone=contact_phone,
                scheduled_delivery_time=scheduled_time,
                is_scheduled=scheduled_time is not None,
            )
        except ValueError as e:
            raise serializers.ValidationError({"cart": str(e)})

        return order


class PlaceOrderSerializer(serializers.Serializer):
    pass


class UpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_status(self, value):
        order = self.context.get("order")
        if order and not order.can_transition_to(value):
            raise serializers.ValidationError(
                f"لا يمكن الانتقال من {order.get_status_display()} إلى {OrderStatus(value).label}"
            )
        return value


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        order = self.context.get("order")
        if order and not order.can_cancel:
            raise serializers.ValidationError("لا يمكن إلغاء هذا الطلب")
        return attrs


# ===== Driver Serializers =====


class DriverOrderRequestSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    restaurant_name = serializers.CharField(
        source="order.restaurant.name", read_only=True, allow_null=True
    )
    restaurant_name_manual = serializers.CharField(
        source="order.restaurant_name_manual", read_only=True
    )
    restaurant_address = serializers.CharField(
        source="order.restaurant.address", read_only=True, allow_null=True
    )
    delivery_address = serializers.JSONField(
        source="order.address_snapshot", read_only=True
    )
    total = serializers.DecimalField(
        source="order.total", max_digits=10, decimal_places=2, read_only=True
    )
    restaurant_total = serializers.DecimalField(
        source="order.restaurant_total", max_digits=10, decimal_places=2, read_only=True
    )
    items_count = serializers.IntegerField(source="order.items_count", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_manual = serializers.BooleanField(source="order.is_manual", read_only=True)
    is_price_pending = serializers.BooleanField(
        source="order.is_price_pending", read_only=True
    )
    description = serializers.CharField(source="order.description", read_only=True)
    delivery_address_text = serializers.CharField(
        source="order.delivery_address_text", read_only=True
    )
    contact_phone = serializers.CharField(source="order.contact_phone", read_only=True)
    user_location_link = serializers.SerializerMethodField()

    # حقول موحدة للدرايفر
    display_restaurant_name = serializers.SerializerMethodField()
    display_restaurant_address = serializers.SerializerMethodField()
    display_delivery_address = serializers.SerializerMethodField()
    display_user_phone = serializers.SerializerMethodField()

    class Meta:
        model = DriverOrderRequest
        fields = [
            "id",
            "order",
            "order_number",
            "is_manual",
            "is_price_pending",
            "description",
            "delivery_address_text",
            "restaurant_name",
            "restaurant_name_manual",
            "restaurant_address",
            "delivery_address",
            "contact_phone",
            "user_location_link",
            "total",
            "restaurant_total",
            "items_count",
            "action",
            "action_display",
            "distance_km",
            "sent_at",
            "responded_at",
            "is_expired",
            # موحدة
            "display_restaurant_name",
            "display_restaurant_address",
            "display_delivery_address",
            "display_user_phone",
        ]

    def get_user_location_link(self, obj):
        snapshot = obj.order.address_snapshot
        lat, lng = None, None
        if snapshot and isinstance(snapshot, dict):
            lat = snapshot.get("latitude")
            lng = snapshot.get("longitude")
        if not lat or not lng:
            addr = obj.order.delivery_address
            if addr and addr.latitude and addr.longitude:
                lat = str(addr.latitude)
                lng = str(addr.longitude)
        if lat and lng:
            return f"https://www.google.com/maps?q={lat},{lng}"
        return None

    def get_display_restaurant_name(self, obj):
        order = obj.order
        if order.restaurant:
            return order.restaurant.name
        return order.restaurant_name_manual or "غير محدد"

    def get_display_restaurant_address(self, obj):
        order = obj.order
        if order.restaurant:
            return order.restaurant.address
        return order.restaurant_snapshot.get("address", "غير محدد")

    def get_display_delivery_address(self, obj):
        order = obj.order
        if order.address_snapshot:
            return order.address_snapshot.get("full_address")
        return order.delivery_address_text or "غير محدد"

    def get_display_user_phone(self, obj):
        order = obj.order
        if order.contact_phone:
            return order.contact_phone
        if order.user:
            return order.user.phone_number
        return None


class AcceptOrderRequestSerializer(serializers.Serializer):
    pass


class RejectOrderRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class DriverOrderListSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source="restaurant.name", read_only=True, allow_null=True
    )
    restaurant_address = serializers.CharField(
        source="restaurant.address", read_only=True, allow_null=True
    )
    restaurant_phone = serializers.CharField(
        source="restaurant.phone", read_only=True, allow_null=True
    )
    user_name = serializers.CharField(
        source="user.full_name", read_only=True, allow_null=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True, allow_null=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    delivery_address = serializers.JSONField(source="address_snapshot", read_only=True)

    # حقول موحدة للدرايفر
    display_restaurant_name = serializers.SerializerMethodField()
    display_restaurant_address = serializers.SerializerMethodField()
    display_delivery_address = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "is_manual",
            "is_price_pending",
            "description",
            "delivery_address_text",
            "restaurant_name_manual",
            "status",
            "status_display",
            "restaurant",
            "restaurant_name",
            "restaurant_address",
            "restaurant_phone",
            "user",
            "user_name",
            "user_phone",
            "contact_phone",
            "delivery_address",
            "total",
            "restaurant_total",
            "items_count",
            "is_scheduled",
            "scheduled_delivery_time",
            "placed_at",
            "confirmed_at",
            "preparing_at",
            "picked_at",
            "created_at",
            # موحدة
            "display_restaurant_name",
            "display_restaurant_address",
            "display_delivery_address",
        ]

    def get_display_restaurant_name(self, obj):
        if obj.restaurant:
            return obj.restaurant.name
        return obj.restaurant_name_manual or "غير محدد"

    def get_display_restaurant_address(self, obj):
        if obj.restaurant:
            return obj.restaurant.address
        return obj.restaurant_snapshot.get("address", "غير محدد")

    def get_display_delivery_address(self, obj):
        if obj.address_snapshot:
            return obj.address_snapshot.get("full_address")
        return obj.delivery_address_text or "غير محدد"


class DriverOrderDetailSerializer(OrderDetailSerializer):
    user_name = serializers.CharField(
        source="user.full_name", read_only=True, allow_null=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True, allow_null=True
    )

    class Meta(OrderDetailSerializer.Meta):
        fields = OrderDetailSerializer.Meta.fields + ["user_name", "user_phone"]


class DriverUpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            (OrderStatus.PICKED, "تم الاستلام"),
            (OrderStatus.DELIVERED, "تم التوصيل"),
        ]
    )

    def validate_status(self, value):
        order = self.context.get("order")
        allowed_transitions = {
            OrderStatus.PREPARING: [OrderStatus.PICKED],
            OrderStatus.PICKED: [OrderStatus.DELIVERED],
        }
        if order:
            # إذا كان السعر معلقاً لا يمكن تحديث الحالة لـ DELIVERED
            if value == OrderStatus.DELIVERED and order.is_price_pending:
                raise serializers.ValidationError(
                    "يجب تحديد سعر الطلب أولاً قبل تأكيد التوصيل"
                )
            allowed = allowed_transitions.get(order.status, [])
            if value not in allowed:
                raise serializers.ValidationError(
                    f"لا يمكن تحديث الحالة من {order.get_status_display()} إلى {OrderStatus(value).label}"
                )
        return value


class DriverSetOrderPriceSerializer(serializers.Serializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate_subtotal(self, value):
        if value <= 0:
            raise serializers.ValidationError("السعر يجب أن يكون أكبر من صفر")
        return value

    def validate(self, attrs):
        order = self.context["order"]
        if not order.is_price_pending:
            raise serializers.ValidationError("هذا الطلب لا يحتاج تحديد سعر")
        if order.status != OrderStatus.PICKED:
            raise serializers.ValidationError(
                "يمكن تحديد السعر فقط بعد استلام الطلب من المحل"
            )
        return attrs


class OrderDeliveryReportImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDeliveryReportImage
        fields = ["id", "image", "caption"]


class CreateDeliveryReportSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=5,
    )

    def validate(self, attrs):
        order = self.context["order"]
        if order.status != OrderStatus.DELIVERED:
            raise serializers.ValidationError("يمكن إرسال التقرير فقط بعد تسليم الطلب")
        if hasattr(order, "delivery_report"):
            raise serializers.ValidationError("تم إرسال تقرير لهذا الطلب مسبقاً")
        return attrs

    def create(self, validated_data):
        order = self.context["order"]
        driver = self.context["driver"]
        images = validated_data.pop("images", [])

        report = OrderDeliveryReport.objects.create(
            order=order,
            driver=driver,
            notes=validated_data.get("notes", ""),
        )
        for image in images:
            OrderDeliveryReportImage.objects.create(report=report, image=image)
        return report


class OrderDeliveryReportSerializer(serializers.ModelSerializer):
    images = OrderDeliveryReportImageSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    driver_name = serializers.CharField(
        source="driver.full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = OrderDeliveryReport
        fields = [
            "id",
            "order",
            "order_number",
            "driver",
            "driver_name",
            "notes",
            "images",
            "created_at",
        ]


# ===== Admin Serializers =====


class AdminOrderListSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source="restaurant.name", read_only=True, allow_null=True
    )
    restaurant_phone = serializers.CharField(
        source="restaurant.phone", read_only=True, allow_null=True
    )
    restaurant_logo = serializers.ImageField(
        source="restaurant.logo", read_only=True, allow_null=True
    )
    # status already comes as English (e.g. "placed", "preparing")
    # just remove status_display or make it return the raw value
    status_display = serializers.CharField(source="status", read_only=True)
    user_name = serializers.CharField(
        source="user.full_name", read_only=True, allow_null=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True, allow_null=True
    )
    # Same for payment_method - raw value is already English
    payment_method_display = serializers.CharField(
        source="payment_method", read_only=True
    )
    display_restaurant_name = serializers.SerializerMethodField()
    order_type_display = serializers.SerializerMethodField()
    delivery_type_display = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()
    driver_phone = serializers.CharField(
        source="driver.phone_number", read_only=True, allow_null=True
    )
    has_driver = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "is_manual",
            "chat_order_id",
            "order_type_display",
            "status",
            "status_display",
            "user",
            "user_name",
            "user_phone",
            "contact_phone",
            "restaurant",
            "restaurant_name",
            "restaurant_phone",
            "restaurant_logo",
            "restaurant_name_manual",
            "display_restaurant_name",
            "subtotal",
            "delivery_fee",
            "discount_amount",
            "total",
            "restaurant_total",
            "app_discount_percentage",
            "payment_method",
            "payment_method_display",
            "payment_status",
            "is_price_pending",
            "delivery_type_display",
            "is_scheduled",
            "scheduled_delivery_time",
            "driver",
            "driver_name",
            "driver_phone",
            "has_driver",
            "items_count",
            "placed_at",
            "created_at",
        ]

    def get_display_restaurant_name(self, obj):
        if obj.restaurant:
            return obj.restaurant.name
        return obj.restaurant_name_manual or "N/A"

    def get_order_type_display(self, obj):
        return "manual" if obj.is_manual else "regular"

    def get_delivery_type_display(self, obj):
        return "scheduled" if obj.is_scheduled else "instant"

    def get_driver_name(self, obj):
        if not obj.driver:
            return None
        hero = getattr(obj.driver, "hero", None)
        if hero:
            return f"#{hero.number}"
        return obj.driver.full_name

    def get_has_driver(self, obj):
        return obj.driver is not None


class AdminOrderDetailSerializer(OrderDetailSerializer):
    restaurant_phone = serializers.CharField(
        source="restaurant.phone", read_only=True, allow_null=True
    )
    restaurant_logo = serializers.ImageField(
        source="restaurant.logo", read_only=True, allow_null=True
    )
    user_name = serializers.CharField(
        source="user.full_name", read_only=True, allow_null=True
    )
    user_phone = serializers.CharField(
        source="user.phone_number", read_only=True, allow_null=True
    )
    # Override to English (parent uses get_status_display which is Arabic)
    status_display = serializers.CharField(source="status", read_only=True)
    payment_method_display = serializers.CharField(
        source="payment_method", read_only=True
    )
    payment_status_display = serializers.CharField(
        source="payment_status", read_only=True
    )

    display_restaurant_name = serializers.SerializerMethodField()
    order_type_display = serializers.SerializerMethodField()
    delivery_type_display = serializers.SerializerMethodField()
    has_driver = serializers.SerializerMethodField()
    coupon_details = serializers.SerializerMethodField()
    financial_summary = serializers.SerializerMethodField()

    class Meta(OrderDetailSerializer.Meta):
        fields = OrderDetailSerializer.Meta.fields + [
            "is_manual",
            "chat_order_id",
            "order_type_display",
            "delivery_type_display",
            "display_restaurant_name",
            "restaurant_logo",
            "restaurant_phone",
            "restaurant_name_manual",
            "user_name",
            "user_phone",
            "has_driver",
            "app_discount_percentage",
            "delivery_address_text",
            "description",
            "coupon_details",
            "financial_summary",
        ]

    def get_display_restaurant_name(self, obj):
        if obj.restaurant:
            return obj.restaurant.name
        return obj.restaurant_name_manual or "N/A"

    def get_order_type_display(self, obj):
        return "manual" if obj.is_manual else "regular"

    def get_delivery_type_display(self, obj):
        return "scheduled" if obj.is_scheduled else "instant"

    def get_has_driver(self, obj):
        return obj.driver is not None

    def get_coupon_details(self, obj):
        if not obj.coupon:
            return None
        coupon = obj.coupon
        coupon_discount = obj.subtotal + obj.delivery_fee - obj.total
        return {
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
            "coupon_discount": str(coupon_discount),
        }

    def get_financial_summary(self, obj):
        from decimal import Decimal

        # حساب سعر المنتجات قبل الخصم من items_snapshot
        subtotal_before_discount = Decimal("0")
        if obj.items_snapshot:
            for item in obj.items_snapshot:
                base = Decimal(str(item.get("base_price", "0")))
                qty = int(item.get("quantity", 1))
                variation = item.get("variation")
                if variation:
                    base += Decimal(str(variation.get("price_adjustment", "0")))
                addons_total = Decimal("0")
                for addon in item.get("addons", []):
                    addons_total += Decimal(str(addon.get("price", "0"))) * int(addon.get("quantity", 1))
                subtotal_before_discount += (base + addons_total) * qty

        # خصم المطعم/المنتج = الفرق بين السعر الأصلي والسعر بعد الخصم
        product_discount = subtotal_before_discount - obj.subtotal

        # خصم الكوبون
        coupon_discount = obj.subtotal + obj.delivery_fee - obj.total

        # عمولة التطبيق من المنتجات
        app_commission = obj.subtotal - obj.restaurant_total

        # ربح التطبيق
        app_revenue = app_commission + obj.delivery_fee - coupon_discount

        return {
            "subtotal_before_discount": str(subtotal_before_discount),
            "product_discount": str(product_discount),
            "subtotal": str(obj.subtotal),
            "delivery_fee": str(obj.delivery_fee),
            "coupon_discount": str(coupon_discount),
            "total": str(obj.total),
            "restaurant_total": str(obj.restaurant_total),
            "app_discount_percentage": str(obj.app_discount_percentage),
            "app_commission": str(app_commission),
            "app_revenue": str(app_revenue),
        }


class AdminUpdateOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            (OrderStatus.CONFIRMED, "تم تأكيد الطلب"),
            (OrderStatus.PREPARING, "جاري التحضير"),
            (OrderStatus.CANCELLED, "ملغي"),
        ]
    )
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["status"] == OrderStatus.CANCELLED and not attrs.get("reason"):
            raise serializers.ValidationError({"reason": "سبب الإلغاء مطلوب"})
        return attrs


class CreateManualOrderSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=["external", "chat"])

    # معلومات المستخدم
    user_id = serializers.IntegerField(required=False, allow_null=True)
    contact_phone = serializers.CharField(max_length=20)

    # معرف طلب الشات
    chat_order_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )

    # معلومات المطعم
    restaurant_id = serializers.IntegerField(required=False, allow_null=True)
    restaurant_name_manual = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    restaurant_address_manual = serializers.CharField(
        required=False, allow_blank=True, help_text="عنوان المطعم إذا لم يكن مسجلاً"
    )

    # العنوان
    delivery_address_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_address_text = serializers.CharField(required=False, allow_blank=True)

    # تفاصيل الطلب
    description = serializers.CharField()
    subtotal = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal("0")
    )
    delivery_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal("0")
    )
    restaurant_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal("0")
    )

    # السعر المعلق
    is_price_pending = serializers.BooleanField(default=False)

    # الدفع
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )

    # جدولة وملاحظات
    scheduled_delivery_time = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        source = attrs.get("source")

        if source == "chat":
            if not attrs.get("user_id"):
                raise serializers.ValidationError({"user_id": "مطلوب لطلبات الشات"})
            if not attrs.get("delivery_address_id"):
                raise serializers.ValidationError(
                    {"delivery_address_id": "مطلوب لطلبات الشات"}
                )
            if not attrs.get("chat_order_id"):
                raise serializers.ValidationError(
                    {"chat_order_id": "مطلوب لطلبات الشات"}
                )

        if source == "external":
            if not attrs.get("delivery_address_text"):
                raise serializers.ValidationError(
                    {"delivery_address_text": "مطلوب للطلبات الخارجية"}
                )

        if attrs.get("restaurant_id") and attrs.get("restaurant_name_manual"):
            raise serializers.ValidationError(
                "لا يمكن تحديد مطعم مسجل واسم مطعم يدوي في نفس الوقت"
            )

        if not attrs.get("restaurant_id") and not attrs.get("restaurant_name_manual"):
            raise serializers.ValidationError("يجب تحديد مطعم أو إدخال اسم المطعم")

        # تقريب رسوم التوصيل لأقرب 1000 لفوق
        import math

        delivery_fee = attrs.get("delivery_fee", Decimal("0"))
        attrs["delivery_fee"] = Decimal(
            str(math.ceil(float(delivery_fee) / 1000) * 1000)
        )

        if not attrs.get("is_price_pending"):
            if attrs.get("subtotal", Decimal("0")) <= 0:
                raise serializers.ValidationError(
                    {"subtotal": "يجب أن يكون subtotal أكبر من صفر عندما لا يكون السعر معلقاً"}
                )
            if attrs.get("total", Decimal("0")) <= 0:
                raise serializers.ValidationError(
                    {"total": "يجب أن يكون total أكبر من صفر عندما لا يكون السعر معلقاً"}
                )

        # إذا السعر معلق، total = delivery_fee فقط
        if attrs.get("is_price_pending"):
            attrs["subtotal"] = Decimal("0")
            attrs["restaurant_total"] = Decimal("0")
            attrs["total"] = attrs["delivery_fee"]

        return attrs

    def validate_user_id(self, value):
        if value:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            if not User.objects.filter(id=value).exists():
                raise serializers.ValidationError("المستخدم غير موجود")
        return value

    def validate_restaurant_id(self, value):
        if value is not None:
            from restaurants.models import Restaurant

            if not Restaurant.objects.filter(id=value).exists():
                raise serializers.ValidationError("المطعم غير موجود")
        return value

    def validate_delivery_address_id(self, value):
        if value:
            from addresses.models import Address

            user_id = self.initial_data.get("user_id")
            if not Address.objects.filter(id=value, user_id=user_id).exists():
                raise serializers.ValidationError(
                    "العنوان غير موجود أو لا ينتمي لهذا المستخدم"
                )
        return value

    def validate_scheduled_delivery_time(self, value):
        if value:
            min_time = timezone.now() + timezone.timedelta(minutes=30)
            if value < min_time:
                raise serializers.ValidationError(
                    "وقت التوصيل يجب أن يكون بعد 30 دقيقة على الأقل"
                )
        return value

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        from restaurants.models import Restaurant
        from addresses.models import Address

        User = get_user_model()
        admin = self.context["request"].user
        source = validated_data["source"]

        user = None
        if validated_data.get("user_id"):
            user = User.objects.get(id=validated_data["user_id"])

        restaurant = None
        if validated_data.get("restaurant_id"):
            restaurant = Restaurant.objects.get(id=validated_data["restaurant_id"])

        # بناء restaurant_snapshot
        if restaurant:
            restaurant_snapshot = {
                "id": restaurant.id,
                "name": restaurant.name,
                "address": restaurant.address,
                "phone": restaurant.phone,
            }
        else:
            restaurant_snapshot = {
                "name": validated_data.get("restaurant_name_manual", ""),
                "address": validated_data.get("restaurant_address_manual", ""),
            }

        # معالجة العنوان حسب النوع
        delivery_address = None
        delivery_address_text = validated_data.get("delivery_address_text", "")
        address_snapshot = {}

        if source == "chat":
            delivery_address = Address.objects.get(
                id=validated_data["delivery_address_id"]
            )
            delivery_address_text = delivery_address.full_address
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

        scheduled_time = validated_data.get("scheduled_delivery_time")
        is_scheduled = scheduled_time is not None

        # المجدول يبدأ PLACED وينتظر Celery يحوله لـ PREPARING
        # غير المجدول يبدأ PREPARING مباشرة
        initial_status = OrderStatus.PLACED if is_scheduled else OrderStatus.PREPARING

        # ── حساب restaurant_total تلقائياً — المنطق المصحح ──
        subtotal = validated_data["subtotal"]
        app_discount_pct = Decimal("0")
        restaurant_total = validated_data.get("restaurant_total", Decimal("0"))

        if restaurant and subtotal > 0:
            app_discount_pct = restaurant.app_discount_percentage or Decimal("0")

            has_customer_discount = (
                restaurant.has_discount and restaurant.current_discount
            )

            if has_customer_discount:
                # الخصم للزبون — المطعم ياخد كامل
                restaurant_total = subtotal
            else:
                # عمولة للشركة
                if app_discount_pct > 0:
                    restaurant_total = subtotal - (
                        subtotal * app_discount_pct / Decimal("100")
                    )
                else:
                    restaurant_total = subtotal

        # رقم الطلب = chat_order_id لطلبات الشات
        order_number = ""
        if source == "chat" and validated_data.get("chat_order_id"):
            order_number = validated_data["chat_order_id"]

        order = Order.objects.create(
            order_number=order_number,
            user=user,
            restaurant=restaurant,
            restaurant_name_manual=validated_data.get("restaurant_name_manual", ""),
            is_manual=True,
            chat_order_id=validated_data.get("chat_order_id", ""),
            created_by=admin,
            description=validated_data["description"],
            delivery_address=delivery_address,
            delivery_address_text=delivery_address_text,
            address_snapshot=address_snapshot,
            restaurant_snapshot=restaurant_snapshot,
            contact_phone=validated_data["contact_phone"],
            payment_method=validated_data["payment_method"],
            notes=validated_data.get("notes", ""),
            subtotal=subtotal,
            delivery_fee=validated_data["delivery_fee"],
            discount_amount=Decimal("0"),
            total=validated_data["total"],
            restaurant_total=restaurant_total,
            app_discount_percentage=app_discount_pct,
            is_price_pending=validated_data.get("is_price_pending", False),
            scheduled_delivery_time=scheduled_time,
            is_scheduled=is_scheduled,
            status=initial_status,
        )

        source_label = "من الشات" if source == "chat" else "خارجي"
        if is_scheduled:
            note = f"طلب يدوي مجدول {source_label} أنشأه الأدمن — ينتظر وقت التوصيل"
        else:
            note = f"طلب يدوي {source_label} أنشأه الأدمن"

        OrderStatusHistory.objects.create(
            order=order,
            from_status=OrderStatus.DRAFT,
            to_status=initial_status,
            changed_by=admin,
            notes=note,
        )

        return order


