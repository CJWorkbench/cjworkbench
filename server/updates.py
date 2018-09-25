# Check for updated data
import logging
from server.models import WfModule
from server.dispatch import module_dispatch_event
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


# update all modules' data. But only ever one at a time,
async def update_wfm_data_scan():
    logger.debug('Scanning for updating modules')

    now = timezone.now()

    wf_modules = list(
        WfModule.objects
        .filter(workflow__isnull=False)  # ignore deleted WfModules
        .filter(auto_update_data=True)  # user wants auto-update
        .filter(next_update__lte=now)  # enough time has passed
    )

    for wf_module in wf_modules:
        await update_wf_module(wf_module, now)


async def update_wf_module(wf_module, now):
    """Fetch `wf_module` and notify user of changes via email/websockets."""
    logger.debug(f'Updating {wf_module} - interval '
                 f'{wf_module.update_interval}')
    with wf_module.workflow.cooperative_lock():
        try:
            await module_dispatch_event(wf_module)
            # Only set last_update_check if succeeded. TODO reconsider.
            wf_module.last_update_check = now
        except Exception as e:
            # Log exceptions but keep going
            logger.exception(f'Error fetching {wf_module}')

        update_next_update_time(wf_module, now)


def update_next_update_time(wf_module, now):
    """Schedule next update, skipping missed updates if any."""
    tick = timedelta(seconds=max(wf_module.update_interval, 1))

    while wf_module.next_update <= now:
        wf_module.next_update += tick
    wf_module.save(update_fields=['last_update_check', 'next_update'])
