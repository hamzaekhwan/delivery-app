"""
Core Constants - All application constants and choices
"""

from django.db import models


class OrderStatus(models.TextChoices):
    """Order lifecycle statuses"""

    DRAFT = "draft", "مسودة"
    PLACED = "placed", "تم الطلب"
    CONFIRMED = "confirmed", "تمت الموافقة"
    PREPARING = "preparing", "جاري التحضير"
    PICKED = "picked", "تم الاستلام"
    DELIVERED = "delivered", "تم التوصيل"
    CANCELLED = "cancelled", "ملغي"


class PaymentMethod(models.TextChoices):
    """Payment methods"""

    CASH = "cash", "نقدي"
    CARD = "card", "بطاقة"
    WALLET = "wallet", "محفظة"


class PaymentStatus(models.TextChoices):
    """Payment statuses"""

    PENDING = "pending", "معلق"
    PAID = "paid", "مدفوع"
    FAILED = "failed", "فشل"
    REFUNDED = "refunded", "مسترد"


class RestaurantType(models.TextChoices):
    """Restaurant/Store types"""

    FOOD = "food", "مطعم"
    GROCERY = "grocery", "بقالة"
    PHARMACY = "pharmacy", "صيدلية"
    SWEETS = "sweets", "حلويات"
    BAKERY = "bakery", "مخبز"
    COFFEE = "coffee", "قهوة"
    OTHER = "other", "أخرى"


class DriverStatus(models.TextChoices):
    """Driver availability status"""

    OFFLINE = "offline", "غير متصل"
    ONLINE = "online", "متصل"
    BUSY = "busy", "مشغول"


class DriverOrderAction(models.TextChoices):
    """Driver actions on orders"""

    PENDING = "pending", "بانتظار الرد"
    ACCEPTED = "accepted", "مقبول"
    REJECTED = "rejected", "مرفوض"
    EXPIRED = "expired", "منتهي"


class DiscountType(models.TextChoices):
    """Discount types for coupons and products"""

    PERCENTAGE = "percentage", "نسبة مئوية"
    FIXED = "fixed", "مبلغ ثابت"
    FREE_DELIVERY = "free_delivery", "توصيل مجاني"  # ← جديد


class CouponStatus(models.TextChoices):
    """Coupon statuses"""

    ACTIVE = "active", "نشط"
    INACTIVE = "inactive", "غير نشط"
    EXPIRED = "expired", "منتهي"


class NotificationType(models.TextChoices):
    """Notification types"""

    ORDER_PLACED = "order_placed", "طلب جديد"
    ORDER_CONFIRMED = "order_confirmed", "تم تأكيد الطلب"
    ORDER_PREPARING = "order_preparing", "جاري تحضير الطلب"
    ORDER_PICKED = "order_picked", "تم استلام الطلب"
    ORDER_DELIVERED = "order_delivered", "تم توصيل الطلب"
    ORDER_CANCELLED = "order_cancelled", "تم إلغاء الطلب"
    DRIVER_ASSIGNED = "driver_assigned", "تم تعيين سائق"
    NEW_ORDER_FOR_DRIVER = "new_order_for_driver", "طلب جديد للسائق"
    NEW_ORDER_FOR_ADMIN = "new_order_for_admin", "طلب جديد للأدمن"  # ← هذا
    PROMOTION = "promotion", "عرض ترويجي"
    GENERAL = "general", "عام"


# Order status transitions
ORDER_STATUS_TRANSITIONS = {
    OrderStatus.DRAFT: [OrderStatus.PLACED, OrderStatus.CANCELLED],
    OrderStatus.PLACED: [
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.CANCELLED,
    ],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.PICKED, OrderStatus.CANCELLED],
    OrderStatus.PICKED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


# Notification messages templates
NOTIFICATION_MESSAGES = {
    NotificationType.ORDER_PLACED: {
        "title": "طلب جديد",
        "body": "تم استلام طلبك رقم #{order_number} بنجاح",
        "title_en": "New Order",
        "body_en": "Your order #{order_number} has been received",
    },
    NotificationType.ORDER_CONFIRMED: {
        "title": "تم تأكيد الطلب",
        "body": "تم تأكيد طلبك المجدول رقم #{order_number}",
        "title_en": "Order Confirmed",
        "body_en": "Your scheduled order #{order_number} has been confirmed",
    },
    NotificationType.ORDER_PREPARING: {
        "title": "جاري التحضير",
        "body": "جاري تحضير طلبك رقم #{order_number}",
        "title_en": "Preparing",
        "body_en": "Your order #{order_number} is being prepared",
    },
    NotificationType.ORDER_PICKED: {
        "title": "تم استلام الطلب",
        "body": "{driver_name} استلم طلبك رقم #{order_number} وفي الطريق إليك",
        "title_en": "Order Picked Up",
        "body_en": "{driver_name} picked up your order #{order_number} and is on the way",
    },
    NotificationType.ORDER_DELIVERED: {
        "title": "تم التوصيل",
        "body": "تم توصيل طلبك رقم #{order_number} بنجاح",
        "title_en": "Order Delivered",
        "body_en": "Your order #{order_number} has been delivered",
    },
    NotificationType.ORDER_CANCELLED: {
        "title": "تم إلغاء الطلب",
        "body": "تم إلغاء طلبك رقم #{order_number}",
        "title_en": "Order Cancelled",
        "body_en": "Your order #{order_number} has been cancelled",
    },
    NotificationType.DRIVER_ASSIGNED: {
        "title": "تم تعيين سائق",
        "body": "السائق {driver_name} سيقوم بتوصيل طلبك",
        "title_en": "Driver Assigned",
        "body_en": "Driver {driver_name} will deliver your order",
    },
    NotificationType.NEW_ORDER_FOR_DRIVER: {
        "title": "طلب جديد",
        "body": "لديك طلب جديد من {restaurant_name}",
        "title_en": "New Order",
        "body_en": "You have a new order from {restaurant_name}",
    },
}
