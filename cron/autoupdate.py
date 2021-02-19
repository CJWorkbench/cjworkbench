import datetime
import logging
from typing import List, Tuple

from cjworkbench.pg_render_locker import PgRenderLocker, WorkflowAlreadyLocked
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Step


logger = logging.getLogger(__name__)


@database_sync_to_async
def load_pending_steps() -> List[Tuple[int, Step]]:
    """Return list of (workflow_id, step_id) with pending fetches."""
    now = datetime.datetime.now()
    # Step.workflow_id is a database operation
    return list(
        Step.objects.filter(
            is_deleted=False,
            tab__is_deleted=False,
            is_busy=False,  # not already scheduled
            auto_update_data=True,  # user wants auto-update
            next_update__isnull=False,  # DB isn't inconsistent
            next_update__lte=now,  # enough time has passed
        ).values_list("tab__workflow_id", "id")
    )


@database_sync_to_async
def set_step_busy(step_id):
    # Database writes can't be on the event-loop thread
    Step.objects.filter(id=step_id).update(is_busy=True)


async def queue_fetches(pg_render_locker: PgRenderLocker):
    """Queue all pending fetches in RabbitMQ.

    We'll set is_busy=True as we queue them, so we don't send double-fetches.
    """
    pending_ids = await load_pending_steps()

    for workflow_id, step_id in pending_ids:
        # Don't schedule a fetch if we're currently rendering.
        #
        # This still lets us schedule a fetch if a render is _queued_, so it
        # doesn't solve any races. But it should lower the number of fetches of
        # resource-intensive workflows.
        #
        # Using pg_render_locker means we can only queue a fetch _between_
        # renders. The fetch/render queues may be non-empty (we aren't
        # checking); but we're giving the renderers a chance to tackle some
        # backlog.
        try:
            async with pg_render_locker.render_lock(workflow_id) as lock:
                # At this moment, the workflow isn't rendering. Let's pass
                # through and queue the fetch.
                await lock.stall_others()  # required by the PgRenderLocker API

            logger.info("Queue fetch of step(%d, %d)", workflow_id, step_id)
            await set_step_busy(step_id)
            await rabbitmq.send_update_to_workflow_clients(
                workflow_id,
                clientside.Update(steps={step_id: clientside.StepUpdate(is_busy=True)}),
            )
            await rabbitmq.queue_fetch(workflow_id, step_id)
        except WorkflowAlreadyLocked:
            # Don't queue a fetch. We'll revisit this Step next time we
            # query for pending fetches.
            pass
