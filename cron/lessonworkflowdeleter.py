import datetime
import logging
import time
from datetime import timedelta

import django
import django.db

from cjworkbench.util import benchmark_sync


LessonFreshDuration = 30 * 86400  # seconds
Interval = 300  # seconds


logger = logging.getLogger(__name__)


def delete_stale_lesson_workflows() -> None:
    from cjwstate.models import Workflow  # after django.setup()

    now = datetime.datetime.now()
    expire_date = now - timedelta(seconds=LessonFreshDuration)
    to_delete = list(
        Workflow.objects.filter(
            lesson_slug__isnull=False, last_viewed_at__lt=expire_date
        ).values_list("id", flat=True)
    )

    for workflow_id in to_delete:
        try:
            with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow:
                logger.info("Deleting workflow %d", workflow_id)
                workflow.delete()
        except Workflow.DoesNotExist:
            logger.info(
                "Tried to delete workflow %d, but it was deleted before we could",
                workflow_id,
            )


if __name__ == "__main__":
    django.setup()

    while True:
        with benchmark_sync(logger, "Deleting stale lesson workflows"):
            delete_stale_lesson_workflows()
        time.sleep(Interval)
