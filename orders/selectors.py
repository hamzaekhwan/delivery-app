"""
Orders Selectors - Data fetching and query logic
"""

from django.utils import timezone
from django.db.models import Q, QuerySet
from .models import Order, OrderStatus

from core.models import AppConfiguration


def get_scheduled_orders_ready_for_preparation() -> QuerySet[Order]:
    """
    Get scheduled orders that are in CONFIRMED status and their scheduled time
    is within the preparation lead time window.

    Returns orders that should be moved to PREPARING status.
    """
    try:
        # Get preparation lead time from app configuration
        prep_config = AppConfiguration.get_config()
        preparation_lead_minutes = prep_config.preparation_lead_minutes

        # Calculate time window: now + preparation lead time
        current_datetime = timezone.localtime()
        preparation_window = current_datetime + timezone.timedelta(
            minutes=preparation_lead_minutes
        )

        # Use range lookup for better performance
        # Filter scheduled orders that are:
        # 1. In CONFIRMED status
        # 2. Have scheduled delivery time within preparation window
        # 3. Are scheduled orders (is_scheduled=True)
        return (
            Order.objects.filter(
                Q(status=OrderStatus.CONFIRMED)
                & Q(is_scheduled=True)
                & Q(
                    scheduled_delivery_time__range=[
                        current_datetime,
                        preparation_window,
                    ]
                )
            )
            .select_related("user", "driver", "restaurant")
            .prefetch_related("items", "status_history")
            .order_by("scheduled_delivery_time")
        )

    except Exception:
        # Return empty list if there's any error
        return Order.objects.none()
