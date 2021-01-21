import logging
import time
from datetime import timedelta

import django
import django.db
from django.utils import timezone

from cjworkbench.util import benchmark_sync


LessonFreshDuration = 7 * 86400  # seconds
Interval = 300  # seconds


logger = logging.getLogger(__name__)


def disable_stale_auto_update() -> None:
    from cjwstate.models import Step  # after django.setup()

    now = timezone.now()
    expire_date = now - timedelta(seconds=LessonFreshDuration)
    n_disabled = Step.objects.filter(
        next_update__isnull=False,
        is_deleted=False,
        tab__is_deleted=False,
        tab__workflow__lesson_slug__isnull=False,
        tab__workflow__last_viewed_at__lt=expire_date,
    ).update(next_update=None, auto_update_data=False)
    logger.info("Updated %d Steps", n_disabled)


if __name__ == "__main__":
    django.setup()

    while True:
        with benchmark_sync(logger, "Disabling auto-update on stale lessons"):
            disable_stale_auto_update()
        time.sleep(Interval)
