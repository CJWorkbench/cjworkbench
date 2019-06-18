from datetime import timedelta
import logging
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from server.models import WfModule


LessonFreshDuration = 7 * 86400  # seconds


logger = logging.getLogger(__name__)


@database_sync_to_async
def disable_stale_auto_update() -> None:
    now = timezone.now()
    expire_date = now - timedelta(seconds=LessonFreshDuration)
    n_disabled = WfModule.objects.filter(
        next_update__isnull=False,
        is_deleted=False,
        tab__is_deleted=False,
        tab__workflow__lesson_slug__isnull=False,
        tab__workflow__last_viewed_at__lt=expire_date
    ).update(next_update=None, auto_update_data=False)
    logger.info(
        'Set auto_update_data=False on %d WfModules from stale lessons',
        n_disabled
    )
