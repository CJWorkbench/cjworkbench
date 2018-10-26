# Check for updated data
import logging
from datetime import timedelta
from django.utils import timezone
from server import rabbitmq
from server.models import WfModule
from server.dispatch import module_dispatch_fetch

logger = logging.getLogger(__name__)


async def update_wfm_data_scan():
    """
    Queue all pending fetches in RabbitMQ.

    We'll set is_busy=True as we queue them, so we don't send double-fetches.
    """
    logger.debug('Finding stale auto-update WfModules')

    now = timezone.now()
    wf_modules = list(
        WfModule.objects
        .filter(is_busy=False) # not already scheduled
        .filter(workflow__isnull=False)  # not deleted
        .filter(auto_update_data=True)  # user wants auto-update
        .exclude(next_update=None)
        .filter(next_update__lte=now)  # enough time has passed
    )

    for wf_module in wf_modules:
        await wf_module.set_busy()
        await rabbitmq.queue_fetch(wf_module)


async def update_wf_module(wf_module, now):
    """Fetch `wf_module` and notify user of changes via email/websockets."""
    logger.debug(f'Updating {wf_module} - interval '
                 f'{wf_module.update_interval}')
    try:
        await module_dispatch_fetch(wf_module)
    except Exception as e:
        # Log exceptions but keep going
        logger.exception(f'Error fetching {wf_module}')

    update_next_update_time(wf_module, now)


def update_next_update_time(wf_module, now):
    """Schedule next update, skipping missed updates if any."""
    tick = timedelta(seconds=max(wf_module.update_interval, 1))
    wf_module.last_update_check = now

    if wf_module.next_update:
        while wf_module.next_update <= now:
            wf_module.next_update += tick
    wf_module.save(update_fields=['last_update_check', 'next_update'])
