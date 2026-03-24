import logging

from django.db import transaction

from core.constants import OrderStatus

from . import selectors


logger = logging.getLogger(__name__)


@transaction.atomic
def process_scheduled_orders_ready_for_preparation() -> dict[str, int]:
    orders_to_process = selectors.get_scheduled_orders_ready_for_preparation()

    if not orders_to_process:
        return {"processed_count": 0, "failed": 0}

    processed_count = 0
    failed = 0

    for order in orders_to_process:
        try:
            order.update_status(OrderStatus.PREPARING)
            processed_count += 1
        except Exception as e:
            logger.debug(f"Failed to process order {order.order_number} because {e!s}")
            failed += 1

    return {"processed_count": processed_count, "failed": failed}
