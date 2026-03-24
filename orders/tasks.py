import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from . import services

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="orders.process_scheduled_orders_ready_for_preparation",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=360,
)
def process_scheduled_orders_ready_for_preparation_task(self):
    try:
        logger.info("Processing scheduled orders ready for preparation")
        result = services.process_scheduled_orders_ready_for_preparation()
        logger.info(
            f"Processed {result.get('processed_count', 0)} orders, "
            f"failed {result.get('failed', 0)}"
        )
        return result

    except SoftTimeLimitExceeded:
        logger.error("Task exceeded soft time limit, terminating gracefully.")
        raise

    except Exception as e:
        logger.error(
            f"Task failed on attempt {self.request.retries + 1}: {e}", exc_info=True
        )
        raise self.retry(exc=e, countdown=10)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.critical(
            f"Task {task_id} permanently failed after {self.max_retries} retries: {exc}",
            exc_info=True,
        )
        # notify_sentry(exc)
        # send_alert_to_slack(exc)
