import logging
from typing import List, Tuple
from channels.db import database_sync_to_async
from django.utils import timezone
from server import rabbitmq, websockets
from server.models import WfModule
from worker.pg_locker import PgLocker, WorkflowAlreadyLocked


logger = logging.getLogger(__name__)


@database_sync_to_async
def load_pending_wf_modules() -> List[Tuple[int, WfModule]]:
    """Return list of (workflow_id, wf_module) with pending fetches."""
    now = timezone.now()
    # WfModule.workflow_id is a database operation
    return [(wfm.workflow_id, wfm)
            for wfm in WfModule.objects.filter(
                is_deleted=False,
                tab__is_deleted=False,
                is_busy=False,  # not already scheduled
                auto_update_data=True,  # user wants auto-update
                next_update__isnull=False,  # DB isn't inconsistent
                next_update__lte=now  # enough time has passed
            )]


@database_sync_to_async
def set_wf_module_busy(wf_module):
    # Database writes can't be on the event-loop thread
    wf_module.is_busy = True
    wf_module.save(update_fields=['is_busy'])


async def queue_fetches(pg_locker: PgLocker):
    """
    Queue all pending fetches in RabbitMQ.

    We'll set is_busy=True as we queue them, so we don't send double-fetches.
    """
    wf_modules = await load_pending_wf_modules()

    for workflow_id, wf_module in wf_modules:
        # Don't schedule a fetch if we're currently rendering.
        #
        # This still lets us schedule a fetch if a render is _queued_, so it
        # doesn't solve any races. But it should lower the number of fetches of
        # resource-intensive workflows.
        #
        # Using pg_locker means we can only queue a fetch _between_ renders.
        # The render queue may be non-empty (we aren't testing that); but we're
        # giving the workers a chance to tackle some of the backlog.
        try:
            async with pg_locker.render_lock(workflow_id):
                # At this moment, the workflow isn't rendering. Let's pass
                # through and queue the fetch.
                pass

            logger.info('Queue fetch of wf_module(%d, %d)', workflow_id,
                        wf_module.id)
            await set_wf_module_busy(wf_module)
            await websockets.ws_client_send_delta_async(
                workflow_id,
                {
                    'updateWfModules': {
                        str(wf_module.id): {'is_busy': True, 'fetch_error': ''}
                    }
                }
            )
            await rabbitmq.queue_fetch(wf_module)
        except WorkflowAlreadyLocked:
            # Don't queue a fetch. We'll revisit this WfModule next time we
            # query for pending fetches.
            pass
