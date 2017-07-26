# Check for updated data
from server.models import WfModule
from server.dispatch import module_dispatch_event

# --- Updates ---

def set_update_timer()
    timed_callback(every minute, update_wfm_scan())


# update all modules' data
def update_wfm_data_scan():
    for wfm in WfModule.objects.all():

        # only check if an interval has been set (i.e. this module can load data)
        if wfm.update_interval > 0:
            check_for_wfm_update(wfm)

# Call this periodically corresponding to smallest possible update cycle (currently every minute)
def check_for_wfm_data_update(wfm):
    now = datetime.now()
    if now > wfm.next_update:
        module_dispatch_event(wfm, None)  # equivalent to pressing "check for update" button

        # schedule next update, skipping missed updates if any
        while (wfm.next_update <= now)
            wfm.next_update += timedelta(seconds=wfm.update_interval)
        wfm.save()

