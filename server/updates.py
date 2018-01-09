# Check for updated data
from server.models import WfModule
from server.dispatch import module_dispatch_event
from django.utils import timezone
from datetime import timedelta

# update all modules' data
def update_wfm_data_scan(request):
    # Loop through every workflow module attached to a workflow
    for wfm in WfModule.objects.filter(workflow__isnull=False):
        # only check if an interval has been set (i.e. this module can load data)
        if wfm.auto_update_data and wfm.update_interval>0:
            check_for_wfm_data_update(wfm, request)


# Call this periodically corresponding to smallest possible update cycle (currently every minute)
def check_for_wfm_data_update(wfm, request):
    now = timezone.now()
    if now > wfm.next_update:
        module_dispatch_event(wfm, request=request)
        # schedule next update, skipping missed updates if any
        while (wfm.next_update <= now):
            wfm.next_update += timedelta(seconds=wfm.update_interval)
        wfm.save()
