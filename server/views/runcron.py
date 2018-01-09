# A view that does nothing but trigger our internal job scheduler
# Our external cron job hits this once per minute

from django.http import HttpResponse
from server.updates import update_wfm_data_scan

def runcron(request):

    # This could take a long time, because it can download data for every module.
    # Fortunately django channels distributes requests across workers (4 by default).
    # But if this takes more than 1 minute, we could end up with multiple workers
    # checking for updates at once. Will db locks take care of us if so?
    update_wfm_data_scan(request)

    return HttpResponse(status=204) # no content
