"""
Orders Signals - Event-based order notifications and updates
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory, DriverOrderRequest
from core.constants import OrderStatus, NotificationType, DriverOrderAction
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OrderStatusHistory)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Handle order status changes and trigger notifications"""
    if not created:
        return

    order = instance.order
    new_status = instance.to_status

    try:
        from notifications.services import NotificationService, notify_driver_new_order

        user_notification_map = {
            OrderStatus.PLACED: NotificationType.ORDER_PLACED,
            OrderStatus.CONFIRMED: NotificationType.ORDER_CONFIRMED,
            OrderStatus.PREPARING: NotificationType.ORDER_PREPARING,
            OrderStatus.PICKED: NotificationType.ORDER_PICKED,
            OrderStatus.DELIVERED: NotificationType.ORDER_DELIVERED,
            OrderStatus.CANCELLED: NotificationType.ORDER_CANCELLED,
        }

        notification_type = user_notification_map.get(new_status)
        if notification_type and order.user:
            extra_data = {}
            if new_status == OrderStatus.PICKED:
                driver = getattr(order, "driver", None)
                if driver:
                    hero = getattr(driver, "hero", None)
                    if hero:
                        extra_data["driver_name"] = hero.name
                        extra_data["driver_name_en"] = (
                            hero.name_en or f"Hero #{hero.number}"
                        )
                    else:
                        extra_data["driver_name"] = driver.full_name
                        extra_data["driver_name_en"] = driver.full_name
                else:
                    extra_data["driver_name"] = "السائق"
                    extra_data["driver_name_en"] = "Driver"

            NotificationService.create_order_notification(
                user=order.user,
                order=order,
                notification_type=notification_type.value,
                extra_data=extra_data,
            )

        # Driver assigned notification
        if new_status == OrderStatus.PREPARING and order.driver:
            notify_driver_new_order(driver=order.driver, order=order)

        # إرسال الطلب لجميع السائقين المتاحين عند بدء التحضير
        if new_status == OrderStatus.PREPARING and not order.driver:
            DriverOrderRequest.send_to_all_drivers(order)

        # إشعار الأدمن عند طلب جديد من التطبيق
        if new_status == OrderStatus.PLACED:
            _notify_admins_new_order(order, NotificationService)

        # إشعار الأدمن عند إنشاء طلب يدوي (يبدأ من PREPARING مباشرة)
        if new_status == OrderStatus.PREPARING and order.is_manual:
            _notify_admins_new_order(order, NotificationService)

    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Notification error: {e}")


@receiver(post_save, sender=DriverOrderRequest)
def handle_driver_request_change(sender, instance, created, **kwargs):
    """Handle driver order request changes"""
    if created:
        try:
            from notifications.services import notify_driver_new_order

            notify_driver_new_order(driver=instance.driver, order=instance.order)
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Driver notification error: {e}")

    if instance.action == DriverOrderAction.ACCEPTED:
        try:
            order = instance.order
            if order.restaurant:
                order.restaurant.total_orders += 1
                order.restaurant.save(update_fields=["total_orders"])
        except Exception:
            pass


@receiver(post_save, sender=Order)
def handle_order_delivered(sender, instance, **kwargs):
    """Handle order delivery - update statistics"""
    if instance.status == OrderStatus.DELIVERED:
        try:
            if instance.restaurant:
                instance.restaurant.update_statistics()
        except Exception:
            pass

        if instance.coupon and instance.discount_amount > 0:
            try:
                from coupons.models import CouponUsage

                if not CouponUsage.objects.filter(
                    coupon=instance.coupon, order=instance
                ).exists():
                    CouponUsage.objects.create(
                        coupon=instance.coupon,
                        user=instance.user,
                        order=instance,
                        discount_amount=instance.discount_amount,
                    )
            except Exception:
                pass


def _notify_admins_new_order(order, NotificationService):
    """إرسال إشعار لجميع الأدمن عند طلب جديد"""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admins = User.objects.filter(is_staff=True, is_active=True)

    user_name = order.user.full_name if order.user else order.contact_phone
    restaurant_name = (
        order.restaurant.name
        if order.restaurant
        else order.restaurant_name_manual or "غير محدد"
    )
    order_type = "يدوي" if order.is_manual else "من التطبيق"

    for admin in admins:
        try:
            NotificationService.create_notification(
                user=admin,
                notification_type=NotificationType.NEW_ORDER_FOR_ADMIN.value,
                title=f"طلب جديد 🛒 ({order_type})",
                body=f"طلب #{order.order_number} من {user_name} - {restaurant_name}",
                title_en="New Order",
                body_en=f"Order #{order.order_number} from {restaurant_name}",
                reference_type="order",
                reference_id=order.id,
                data={
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "restaurant_name": restaurant_name,
                    "is_manual": str(order.is_manual),
                },
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin.id}: {e}")
