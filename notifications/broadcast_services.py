"""
Broadcast Services - Business logic for broadcast notifications
"""

import logging
from django.db import transaction
from django.utils import timezone
from typing import TYPE_CHECKING

from .models import BroadcastNotification
from .services import NotificationService

if TYPE_CHECKING:
    from accounts.models import User

logger = logging.getLogger(__name__)


class BroadcastService:
    """Service for broadcast notification operations"""

    @staticmethod
    @transaction.atomic
    def send_broadcast_chunked(
        *, 
        broadcast: BroadcastNotification, 
        chunk_size: int = 500
    ) -> dict[str, int]:
        """
        Send broadcast notification in chunks.
        Uses selector for data, handles business logic only.
        """
        from .selectors import broadcast_get_target_users_chunked
        
        # Get user chunks from selector
        user_chunks = broadcast_get_target_users_chunked(
            broadcast=broadcast, 
            chunk_size=chunk_size
        )
        
        total_users = sum(len(chunk) for chunk in user_chunks)
        successful = 0
        failed = 0
        
        # Process each chunk
        for chunk in user_chunks:
            result = BroadcastService._send_to_user_chunk(
                users=chunk, 
                broadcast=broadcast
            )
            successful += result['successful']
            failed += result['failed']
        
        # Update broadcast statistics
        BroadcastService._update_broadcast_statistics(
            broadcast=broadcast,
            total=total_users,
            successful=successful,
            failed=failed,
        )
        
        logger.info(
            f"Broadcast {broadcast.id} completed: "
            f"total={total_users}, successful={successful}, failed={failed}"
        )
        
        return {"total": total_users, "successful": successful, "failed": failed}

    @staticmethod
    def _send_to_user_chunk(
        *, 
        users: list["User"], 
        broadcast: BroadcastNotification
    ) -> dict[str, int]:
        """Send notifications to a chunk of users."""
        successful = 0
        failed = 0
        
        for user in users:
            try:
                notification = NotificationService.create_notification(
                    user=user,
                    notification_type="promotion",
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
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to create notification for user {user.id}: {e}")
                failed += 1
        
        return {"successful": successful, "failed": failed}

    @staticmethod
    @transaction.atomic
    def _update_broadcast_statistics(
        *, 
        broadcast: BroadcastNotification,
        total: int,
        successful: int,
        failed: int,
    ) -> None:
        """Update broadcast statistics atomically."""
        broadcast.is_sent = True
        broadcast.sent_at = timezone.now()
        broadcast.total_recipients = total
        broadcast.successful_sends = successful
        broadcast.failed_sends = failed
        broadcast.save()

    @staticmethod
    def create_scheduled_broadcast(
        *,
        title: str,
        body: str,
        title_en: str | None = None,
        body_en: str | None = None,
        image_url: str | None = None,
        target_audience: str = "all",
        target_governorate: str | None = None,
        action_type: str | None = None,
        action_data: dict | None = None,
        scheduled_at,
        created_by=None,
    ) -> BroadcastNotification:
        """Create a scheduled broadcast notification with validation."""
        broadcast = BroadcastNotification.objects.create(
            title=title,
            body=body,
            title_en=title_en,
            body_en=body_en,
            image_url=image_url,
            target_audience=target_audience,
            target_governorate=target_governorate,
            action_type=action_type,
            action_data=action_data or {},
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        return broadcast
