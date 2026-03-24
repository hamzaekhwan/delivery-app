"""
Notifications Service - Firebase Cloud Messaging Integration
"""

import logging
from django.conf import settings
from django.utils import timezone
from typing import List, Dict, Optional
from .models import (
    Notification,
    DeviceToken,
    NotificationPreference,
    BroadcastNotification,
)
from core.constants import NotificationType, NOTIFICATION_MESSAGES

logger = logging.getLogger(__name__)


class FCMService:
    """Firebase Cloud Messaging Service - Multi-App Support (User & Driver)"""

    def __init__(self):
        self.user_app = None
        self.driver_app = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK for both User and Driver apps"""
        try:
            import firebase_admin
            from firebase_admin import credentials

            # ── User App ──
            try:
                self.user_app = firebase_admin.get_app("user_app")
            except ValueError:
                cred_path = getattr(settings, "FIREBASE_CREDENTIALS_USER", None)
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    self.user_app = firebase_admin.initialize_app(cred, name="user_app")
                    logger.info("Firebase User App initialized successfully")
                else:
                    logger.warning("FIREBASE_CREDENTIALS_USER not found in settings.")

            # ── Driver App ──
            try:
                self.driver_app = firebase_admin.get_app("driver_app")
            except ValueError:
                cred_path = getattr(settings, "FIREBASE_CREDENTIALS_DRIVER", None)
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    self.driver_app = firebase_admin.initialize_app(
                        cred, name="driver_app"
                    )
                    logger.info("Firebase Driver App initialized successfully")
                else:
                    logger.warning("FIREBASE_CREDENTIALS_DRIVER not found in settings.")

        except ImportError:
            logger.warning("firebase-admin package not installed.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")

    def _get_app_for_user(self, user=None):
        """Return the correct Firebase app based on user role"""
        if user is not None:
            try:
                from accounts.models import User

                if user.role == User.Role.DRIVER:
                    return self.driver_app
            except Exception:
                pass
        return self.user_app

    def send_to_device(
        self, registration_token, title, body, data=None, image_url=None, user=None
    ):
        """Send notification to a single device"""
        app = self._get_app_for_user(user)

        if not app:
            logger.error("Firebase app not initialized")
            return False

        try:
            from firebase_admin import messaging

            notification = messaging.Notification(
                title=title, body=body, image=image_url
            )
            message = messaging.Message(
                notification=notification, data=data or {}, token=registration_token
            )
            response = messaging.send(message, app=app)
            logger.info(f"Successfully sent message: {response}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to device: {str(e)}")
            return False

    def send_to_multiple_devices(
        self, registration_tokens, title, body, data=None, image_url=None, user=None
    ):
        """Send notification to multiple devices"""
        app = self._get_app_for_user(user)

        if not app:
            logger.error("Firebase app not initialized")
            return {
                "success_count": 0,
                "failure_count": len(registration_tokens),
                "failed_tokens": registration_tokens,
            }

        if not registration_tokens:
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}

        try:
            from firebase_admin import messaging

            notification = messaging.Notification(
                title=title, body=body, image=image_url
            )
            message = messaging.MulticastMessage(
                notification=notification, data=data or {}, tokens=registration_tokens
            )
            response = messaging.send_each_for_multicast(message, app=app)

            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(registration_tokens[idx])
                        logger.warning(
                            f"Failed to send to token {registration_tokens[idx][:20]}...: "
                            f"{resp.exception}"
                        )

            logger.info(
                f"Multicast sent. Success: {response.success_count}, "
                f"Failure: {response.failure_count}"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens,
            }
        except Exception as e:
            logger.error(f"Failed to send multicast message: {str(e)}")
            return {
                "success_count": 0,
                "failure_count": len(registration_tokens),
                "failed_tokens": registration_tokens,
            }


# Singleton instance
fcm_service = FCMService()


class NotificationService:
    """Service for handling notifications"""

    @staticmethod
    def create_notification(
        user,
        notification_type: str,
        title: str,
        body: str,
        title_en: str = None,
        body_en: str = None,
        reference_type: str = None,
        reference_id: int = None,
        data: dict = None,
        send_push: bool = True,
    ) -> Notification:
        """Create an in-app notification and optionally send push notification"""
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            title_en=title_en,
            body_en=body_en,
            reference_type=reference_type,
            reference_id=reference_id,
            data=data or {},
        )

        if send_push:
            NotificationService.send_push_notification(notification)

        return notification

    @staticmethod
    def create_order_notification(
        user, order, notification_type: str, extra_data: dict = None
    ) -> Optional[Notification]:
        """Create notification for order events"""
        message_template = NOTIFICATION_MESSAGES.get(notification_type)

        if not message_template:
            for key, value in NOTIFICATION_MESSAGES.items():
                if hasattr(key, "value") and key.value == notification_type:
                    message_template = value
                    break

        if not message_template:
            logger.warning(
                f"No message template for notification type: {notification_type}"
            )
            return None

        title = message_template.get("title", "Order Update")
        title_en = message_template.get("title_en", title)

        body_template = message_template.get("body", "")
        body_en_template = message_template.get("body_en", "")

        # بناء data عربي
        ar_data = dict(extra_data or {})

        # بناء data إنجليزي: استبدال driver_name بـ driver_name_en إذا موجود
        en_data = dict(extra_data or {})
        if "driver_name_en" in en_data:
            en_data["driver_name"] = en_data.pop("driver_name_en")
        else:
            en_data.pop("driver_name_en", None)

        try:
            body = body_template.format(order_number=order.order_number, **ar_data)
        except KeyError:
            body = body_template.format(order_number=order.order_number)

        try:
            body_en = body_en_template.format(
                order_number=order.order_number, **en_data
            )
        except KeyError:
            body_en = body_en_template.format(order_number=order.order_number)

        return NotificationService.create_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            title_en=title_en,
            body_en=body_en,
            reference_type="order",
            reference_id=order.id,
            data={
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
            },
        )

    @staticmethod
    def send_push_notification(notification: Notification) -> bool:
        """Send push notification via Firebase"""
        try:
            preferences = notification.user.notification_preferences
            if not preferences.can_send_notification(notification.notification_type):
                logger.info(f"Notification disabled for user {notification.user.id}")
                return False
        except NotificationPreference.DoesNotExist:
            pass

        device_tokens = list(
            DeviceToken.objects.filter(user=notification.user, is_active=True).values(
                "token", "language"
            )
        )

        if not device_tokens:
            logger.info(f"No device tokens for user {notification.user.id}")
            return False

        # Build data payload - all values must be strings
        data = {
            "notification_id": str(notification.id),
            "type": notification.notification_type,
            "reference_type": notification.reference_type or "",
            "reference_id": str(notification.reference_id)
            if notification.reference_id
            else "",
            "title": notification.title or "",
            "body": notification.body or "",
            "title_en": notification.title_en or "",
            "body_en": notification.body_en or "",
        }

        # Add extra data, converting all values to strings
        for k, v in (notification.data or {}).items():
            data[k] = str(v)

        # Group tokens by language
        ar_tokens = [
            d["token"] for d in device_tokens if d.get("language", "ar") != "en"
        ]
        en_tokens = [d["token"] for d in device_tokens if d.get("language") == "en"]

        total_success = 0
        total_failure = 0
        all_failed_tokens = []

        # Send Arabic push
        if ar_tokens:
            result = fcm_service.send_to_multiple_devices(
                registration_tokens=ar_tokens,
                title=notification.title,
                body=notification.body,
                data=data,
                image_url=notification.image_url,
                user=notification.user,
            )
            total_success += result["success_count"]
            total_failure += result["failure_count"]
            all_failed_tokens.extend(result["failed_tokens"])

        # Send English push
        if en_tokens:
            result = fcm_service.send_to_multiple_devices(
                registration_tokens=en_tokens,
                title=notification.title_en or notification.title,
                body=notification.body_en or notification.body,
                data=data,
                image_url=notification.image_url,
                user=notification.user,
            )
            total_success += result["success_count"]
            total_failure += result["failure_count"]
            all_failed_tokens.extend(result["failed_tokens"])

        if total_success > 0:
            notification.push_sent = True
            notification.push_sent_at = timezone.now()
            notification.save(update_fields=["push_sent", "push_sent_at", "updated_at"])

        # Deactivate failed tokens
        if all_failed_tokens:
            DeviceToken.objects.filter(token__in=all_failed_tokens).update(
                is_active=False
            )

        return total_success > 0

    @staticmethod
    def send_broadcast(broadcast: BroadcastNotification) -> Dict[str, int]:
        """Send broadcast notification to targeted users"""
        from accounts.models import User

        users = User.objects.filter(is_active=True)

        if broadcast.target_audience == "users":
            users = users.filter(role=User.Role.USER)
        elif broadcast.target_audience == "drivers":
            users = users.filter(role=User.Role.DRIVER)
        elif (
            broadcast.target_audience == "governorate" and broadcast.target_governorate
        ):
            users = users.filter(governorate=broadcast.target_governorate)

        total = users.count()
        successful = 0
        failed = 0

        for user in users.iterator():
            try:
                notification = NotificationService.create_notification(
                    user=user,
                    notification_type=NotificationType.PROMOTION.value,
                    title=broadcast.title,
                    body=broadcast.body,
                    title_en=broadcast.title_en,
                    body_en=broadcast.body_en,
                    data={
                        "broadcast_id": broadcast.id,
                        "action_type": broadcast.action_type or "",
                        **broadcast.action_data,
                    },
                )
                if notification:
                    successful += 1
            except Exception as e:
                logger.error(f"Failed to create notification for user {user.id}: {e}")
                failed += 1

        broadcast.is_sent = True
        broadcast.sent_at = timezone.now()
        broadcast.total_recipients = total
        broadcast.successful_sends = successful
        broadcast.failed_sends = failed
        broadcast.save()

        return {"total": total, "successful": successful, "failed": failed}

    @staticmethod
    def mark_all_as_read(user) -> int:
        return Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

    @staticmethod
    def get_unread_count(user) -> int:
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def register_device(
        user,
        token: str,
        device_type: str,
        device_name: str = None,
        language: str = "ar",
    ) -> DeviceToken:
        device, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": user,
                "device_type": device_type,
                "device_name": device_name,
                "language": language,
                "is_active": True,
            },
        )
        return device

    @staticmethod
    def unregister_device(token: str) -> bool:
        return DeviceToken.objects.filter(token=token).update(is_active=False) > 0


def notify_order_status_change(order, new_status):
    type_mapping = {
        "placed": NotificationType.ORDER_PLACED.value,
        "preparing": NotificationType.ORDER_PREPARING.value,
        "picked": NotificationType.ORDER_PICKED.value,
        "delivered": NotificationType.ORDER_DELIVERED.value,
        "cancelled": NotificationType.ORDER_CANCELLED.value,
    }
    notification_type = type_mapping.get(new_status)
    if notification_type:
        extra_data = {}
        if new_status == "picked":
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
            notification_type=notification_type,
            extra_data=extra_data,
        )


def notify_driver_new_order(driver, order):
    NotificationService.create_notification(
        user=driver,
        notification_type=NotificationType.NEW_ORDER_FOR_DRIVER.value,
        title="طلب جديد متاح",
        body=f"يوجد طلب جديد من {order.restaurant.name} بانتظار قبولك",
        title_en="New Order Available",
        body_en=f"New order from {order.restaurant.name} is waiting for your acceptance",
        reference_type="order",
        reference_id=order.id,
        data={
            "order_id": order.id,
            "order_number": order.order_number,
            "restaurant_name": order.restaurant.name,
        },
    )
