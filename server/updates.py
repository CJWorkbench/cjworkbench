# Check for updated data
from server.models import WfModule
from server.dispatch import module_dispatch_event
from server.utils import get_console_logger
from django.utils import timezone
from datetime import timedelta
import threading

logger = get_console_logger()
lock = threading.Lock()

# update all modules' data. But only ever one at a time,
# or we can use up all threads if one request doesn't finish before the next one
def update_wfm_data_scan(request):

    # if we can't get the lock, another thread is already updating, so we won't
    if lock.acquire(blocking=False):
        try:
            logger.debug('Scanning for updating modules')
            # Loop through every workflow module attached to a workflow
            for wfm in WfModule.objects.filter(workflow__isnull=False):
                # only check if an interval has been set (i.e. this module can load data)
                if wfm.auto_update_data and wfm.update_interval>0:
                    check_for_wfm_data_update(wfm, request)
        finally:
            lock.release()


# schedule next update, skipping missed updates if any
def update_next_update_time(wfm, now):
    while (wfm.next_update <= now):
        wfm.next_update += timedelta(seconds=wfm.update_interval)
    wfm.save()

# Call this periodically corresponding to smallest possible update cycle (currently every minute)
def check_for_wfm_data_update(wfm, request):
    now = timezone.now()
    if now > wfm.next_update:
        logger.debug('updating wfm ' + str(wfm) + ' - interval ' +  str(wfm.update_interval))
        try:
            module_dispatch_event(wfm, request=request)
        except Exception as e:
            # Log exceptions but keep going
            update_next_update_time(wfm, now)     # Avoid throwing same exception until time for next update
            logger.exception("Error updating data for module " + str(wfm))
        else:
            # It worked, update the checked time
            wfm.last_update_check = now
            update_next_update_time(wfm, now)
