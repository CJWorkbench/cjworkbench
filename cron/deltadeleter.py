import datetime
import logging
import time

import django
import django.db
from django.db.models import Exists, OuterRef

from cjworkbench.util import benchmark_sync


logger = logging.getLogger(__name__)

MaxNWorkflowsPerCycle = 1000  # SQL LIMIT to avoid too-big query results
Interval = 300  # seconds
MaxAge = datetime.timedelta(days=30)


def delete_workflow_stale_deltas(
    workflow_id: int, min_last_applied_at: datetime.datetime
) -> None:
    from cjwstate.models.workflow import Workflow

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow
            with django.db.connections["default"].cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM delta
                    WHERE workflow_id = %(workflow_id)s
                    AND (
                        id <= (
                            SELECT MAX(delta.id)
                            FROM delta
                            WHERE last_applied_at < %(min_last_applied_at)s
                            AND workflow_id = %(workflow_id)s
                            AND delta.id <= (SELECT last_delta_id FROM workflow WHERE id = %(workflow_id)s)
                        )
                        OR
                        id >= (
                            SELECT MIN(delta.id)
                            FROM delta
                            WHERE last_applied_at < %(min_last_applied_at)s
                            AND workflow_id = %(workflow_id)s
                            AND delta.id > (SELECT last_delta_id FROM workflow WHERE id = %(workflow_id)s)
                        )
                    )
                    """,
                    dict(
                        workflow_id=workflow_id,
                        min_last_applied_at=min_last_applied_at.replace(
                            tzinfo=datetime.timezone.utc
                        ),
                    ),
                )
                # Set the first delta's prev_delta_id to NULL. (The foreign-key
                # constraint is DEFERRABLE INITIALLY DEFERRED.)
                cursor.execute(
                    """
                    UPDATE delta
                    SET prev_delta_id = NULL
                    WHERE id = (
                        SELECT MIN(id) FROM delta WHERE workflow_id = %(workflow_id)s
                    )
                    """,
                    dict(workflow_id=workflow_id),
                )
            workflow.delete_orphan_soft_deleted_models()
    except Workflow.DoesNotExist:
        pass  # Race: I guess there aren't any deltas after all.


def delete_stale_deltas(now: datetime.datetime) -> None:
    """Delete old Deltas.

    Rationale: we want a way to deprecate and then delete bad Commands; and we
    want to speed up database queries by nixing unused data.
    """
    # import _after_ django.setup() initializes apps
    from cjwstate.models.delta import Delta
    from cjwstate.models.workflow import Workflow

    min_last_applied_at = now - MaxAge

    workflow_ids = Workflow.objects.filter(
        Exists(
            Delta.objects.filter(
                last_applied_at__lt=min_last_applied_at.replace(
                    tzinfo=datetime.timezone.utc
                ),
                workflow_id=OuterRef("id"),
            )
        )
    )[:MaxNWorkflowsPerCycle].values_list("id", flat=True)

    for workflow_id in workflow_ids:
        with benchmark_sync(logger, "Deleting old deltas on Workflow %d", workflow_id):
            delete_workflow_stale_deltas(workflow_id, min_last_applied_at)


if __name__ == "__main__":
    django.setup()

    while True:
        django.db.close_old_connections()
        with benchmark_sync(logger, "Deleting old deltas"):
            delete_stale_deltas(datetime.datetime.now())
        time.sleep(Interval)
