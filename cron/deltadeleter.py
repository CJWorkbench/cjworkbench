import datetime
import logging
import time
from typing import List, Tuple

import django
import django.db
from django.db.models import Exists, OuterRef

from cjworkbench.util import benchmark_sync


logger = logging.getLogger(__name__)

MaxNWorkflowsPerCycle = 5000  # SQL LIMIT to avoid too-big query results
Interval = 300  # seconds
MaxAge = datetime.timedelta(days=30)


def delete_workflow_stale_deltas(
    workflow_id: int, min_last_applied_at: datetime.datetime
) -> None:
    from cjwstate.models.workflow import Workflow

    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow:
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
                    # Hack around Work around Postgres picking the wrong index.
                    # [2021-02-02] on production the inner SELECT chose the
                    # delta.id index (id IS NOT NULL) instead of the
                    # delta.workflow_id index (workflow_id = X). Maybe VACUUM
                    # would fix this? Meh. "+ 0" disqualifies the delta.id
                    # index, forcing a better choice.
                    """
                    UPDATE delta
                    SET prev_delta_id = NULL
                    WHERE id = (
                        SELECT MIN(id + 0) FROM delta WHERE workflow_id = %(workflow_id)s
                    )
                    """,
                    dict(workflow_id=workflow_id),
                )
            workflow.delete_orphan_soft_deleted_models()
    except Workflow.DoesNotExist:
        pass  # Race: I guess there aren't any deltas after all.


def find_workflows_with_stale_deltas(
    now: datetime.datetime,
) -> List[Tuple[int, datetime.datetime]]:
    """Query for (workflow_id, min_last_applied_at) pairs."""
    # import _after_ django.setup() initializes apps
    from cjworkbench.models.userlimits import UserLimits

    with django.db.connections["default"].cursor() as cursor:
        cursor.execute(
            """
            WITH
            user_limits AS (
                SELECT
                    subscription.user_id,
                    MAX(product.max_delta_age_in_days) AS max_delta_age_in_days
                FROM subscription
                INNER JOIN price ON price.id = subscription.price_id
                INNER JOIN product ON product.id = price.product_id
                GROUP BY subscription.user_id
            ),
            workflow_ids AS (
                -- Reify as a CTE so when we join with the `workflow` table we
                -- only join one row per ID (instead of one row per delta)
                SELECT workflow_id, MIN(last_applied_at) AS min_last_applied_at
                FROM delta
                GROUP BY workflow_id
            )
            SELECT
                workflow_ids.workflow_id,
                %(now)s - MAKE_INTERVAL(days => GREATEST(
                    user_limits.max_delta_age_in_days, %(default_max_delta_age_in_days)s
                )) AS min_last_applied_at
            FROM workflow_ids
            INNER JOIN workflow ON workflow.id = workflow_ids.workflow_id
            LEFT JOIN user_limits ON user_limits.user_id = workflow.owner_id
            WHERE workflow_ids.min_last_applied_at < %(now)s - MAKE_INTERVAL(days => GREATEST(
                user_limits.max_delta_age_in_days, %(default_max_delta_age_in_days)s
            ))
            LIMIT %(limit)s
            """,
            dict(
                now=now,
                default_max_delta_age_in_days=UserLimits.free_user_limits().max_delta_age_in_days,
                limit=MaxNWorkflowsPerCycle,
            ),
        )
        return [
            (workflow_id, min_last_applied_at.replace(tzinfo=None))
            for workflow_id, min_last_applied_at in cursor.fetchmany(
                MaxNWorkflowsPerCycle
            )
        ]


def delete_stale_deltas(now: datetime.datetime) -> None:
    """Delete old Deltas.

    Rationale: we want a way to deprecate and then delete bad Commands; and we
    want to speed up database queries by nixing unused data.
    """
    with benchmark_sync(logger, "Finding workflows with old deltas"):
        todo = find_workflows_with_stale_deltas(now)

    with benchmark_sync(logger, "Deleting old deltas"):
        for workflow_id, min_last_applied_at in todo:
            with benchmark_sync(
                logger, "Deleting old deltas on Workflow %d", workflow_id
            ):
                delete_workflow_stale_deltas(
                    workflow_id, min_last_applied_at.replace(tzinfo=None)
                )


if __name__ == "__main__":
    django.setup()

    while True:
        django.db.close_old_connections()
        delete_stale_deltas(datetime.datetime.now())
        time.sleep(Interval)
