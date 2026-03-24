from config.env import env

# https://docs.celeryproject.org/en/stable/userguide/configuration.html

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env.str(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/1"
)

CELERY_TIMEZONE = "UTC"

CELERY_TASK_SOFT_TIME_LIMIT = 20  # seconds
CELERY_TASK_TIME_LIMIT = 30  # seconds
CELERY_TASK_MAX_RETRIES = 3

from celery.schedules import crontab  # noqa

CELERY_BEAT_SCHEDULE = {
    "process-scheduled-orders-ready-for-preparation": {
        "task": "orders.process_scheduled_orders_ready_for_preparation",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    "send-scheduled-broadcast-notifications": {
        "task": "notifications.tasks.send_scheduled_broadcast_notifications_task",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
}
