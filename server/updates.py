# Check for updated data
import logging
from datetime import timedelta
from django.utils import timezone
from server import rabbitmq, worker
from server.models import WfModule


logger = logging.getLogger(__name__)


async def update_wfm_data_scan(pg_locker: worker.PgLocker):
    """
    Queue all pending fetches in RabbitMQ.

    We'll set is_busy=True as we queue them, so we don't send double-fetches.
    """
    logger.debug('Finding stale auto-update WfModules')

    now = timezone.now()
    wf_modules = list(
        WfModule.objects
        .filter(is_busy=False)  # not already scheduled
        .filter(workflow__isnull=False)  # not deleted
        .filter(auto_update_data=True)  # user wants auto-update
        .exclude(next_update=None)
        .filter(next_update__lte=now)  # enough time has passed
    )

    for wf_module in wf_modules:
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
            async with pg_locker.render_lock(wf_module.workflow_id):
                # At this moment, the workflow isn't rendering. Let's pass
                # through and queue the fetch.
                pass

            await wf_module.set_busy()
            await rabbitmq.queue_fetch(wf_module)
        except worker.WorkflowAlreadyLocked:
            # Don't queue a fetch. We'll revisit this WfModule next time we
            # query for pending fetches.
            pass
