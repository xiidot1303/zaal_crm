import logging
from django.utils import timezone
from app.models import Room

logger = logging.getLogger(__name__)


def check_room_availability():
    """
    Check rooms that are marked as occupied (is_free=False).
    If taken_to datetime has passed, mark them as free (is_free=True).
    """
    now = timezone.now()

    # Get rooms that are occupied and their taken_to time has passed
    expired_rooms = Room.objects.filter(
        is_free=False,
        taken_to__lte=now
    )

    updated_count = 0
    for room in expired_rooms:
        logger.info(
            f"Room {room.number} occupation expired at {room.taken_to}, "
            f"marking as free (current time: {now})"
        )
        room.is_free = True
        room.taken_to = None
        room.save()
        updated_count += 1

    if updated_count > 0:
        logger.info(f"Updated {updated_count} rooms to free status")
    else:
        logger.debug("No rooms needed status updates")