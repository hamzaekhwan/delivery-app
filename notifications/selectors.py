"""
Notifications Selectors - Database query operations
"""

from django.db import models
from django.utils import timezone
from typing import TYPE_CHECKING

from .models import BroadcastNotification

if TYPE_CHECKING:
    from accounts.models import User


def broadcast_list_pending_scheduled(
    *, filters: dict | None = None
) -> models.QuerySet[BroadcastNotification]:
    """
    Get list of pending scheduled broadcasts whose time has come.
    Excludes minutes, seconds, and microseconds from time comparison.
    Uses local time for timezone comparison.
    """
    filters = filters or {}
    now = timezone.localtime()

    # Get current time without seconds, and microseconds
    current_date_hour = now.replace(second=0, microsecond=0)

    qs = BroadcastNotification.objects.filter(
        scheduled_at__lte=current_date_hour, is_sent=False
    ).order_by("scheduled_at")

    return qs


def broadcast_get_target_users_chunked(
    *, broadcast: BroadcastNotification, chunk_size: int = 500
) -> list[list["User"]]:
    """
    Get target users in chunks using iterator for memory efficiency.
    Returns list of user chunks for processing.
    """
    from accounts.models import User

    users = User.objects.filter(is_active=True)

    if broadcast.target_audience == "users":
        users = users.filter(role=User.Role.USER)
    elif broadcast.target_audience == "drivers":
        users = users.filter(role=User.Role.DRIVER)
    elif broadcast.target_audience == "governorate" and broadcast.target_governorate:
        users = users.filter(governorate=broadcast.target_governorate)

    # Use iterator() for memory efficiency
    chunks = []
    current_chunk = []

    for user in users.iterator(chunk_size=1000):  # Fetch 1000 at a time from DB
        current_chunk.append(user)

        # Create user chunks of desired size
        if len(current_chunk) >= chunk_size:
            chunks.append(current_chunk)
            current_chunk = []

    # Add remaining users
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
