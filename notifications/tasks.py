"""
Notifications Tasks - Celery tasks for background notification processing
"""

import logging
from celery import shared_task

from .broadcast_services import BroadcastService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_scheduled_broadcast_notifications_task(self) -> dict[str, int]:
    """
    Process scheduled broadcasts. Thin task that calls service.
    """
    from .selectors import broadcast_list_pending_scheduled
    
    pending_broadcasts = broadcast_list_pending_scheduled()
    total_processed = 0
    total_successful = 0
    total_failed = 0
    
    for broadcast in pending_broadcasts:
        try:
            result = BroadcastService.send_broadcast_chunked(
                broadcast=broadcast, 
                chunk_size=500
            )
            total_processed += 1
            total_successful += result['successful']
            total_failed += result['failed']
            
            logger.info(
                f"Processed broadcast {broadcast.id}: "
                f"total={result['total']}, successful={result['successful']}, failed={result['failed']}"
            )
            
        except Exception as exc:
            logger.error(f"Failed to process broadcast {broadcast.id}: {exc}")
            
            # Retry logic with exponential backoff
            if self.request.retries < self.max_retries:
                countdown = 2 ** self.request.retries * 60  # 1min, 2min, 4min
                logger.warning(f"Retrying broadcast {broadcast.id} in {countdown} seconds")
                raise self.retry(exc=exc, countdown=countdown)
            else:
                logger.error(f"Max retries exceeded for broadcast {broadcast.id}")
                total_failed += 1
    
    logger.info(
        f"Completed scheduled broadcast notifications task: "
        f"processed={total_processed}, successful={total_successful}, failed={total_failed}"
    )
    
    return {
        'broadcasts_processed': total_processed,
        'total_successful': total_successful,
        'total_failed': total_failed,
    }
