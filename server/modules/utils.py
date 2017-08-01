from server.models import ChangeDataVersionCommand
from server.versions import notify_client_workflow_version_changed
from django.utils import timezone
import math
import pandas as pd
import numpy as np

# Utility class: globals defined for user-entered python code
custom_code_globals = {
    '__builtins__': {},  # disallow import etc. (though still not impossible!)
    'str': str,
    'math' : math,
    'pd' : pd,
    'np' : np
}

# Store retrieved data (in text form here, as csv) if it isn't different from currently stored data
# If it is and auto_change_verssion, switch to new data using a ChangeDataVersion command
def save_data_if_changed(wfm, new_data, auto_change_version=True):

    wfm.last_update_check = timezone.now()
    wfm.save()

    # Check if currently saved data is any different. If so create a new data version and maybe switch to it
    old_data = wfm.retrieve_data()
    if new_data != old_data:
        version = wfm.store_data(new_data)
        if auto_change_version:
            ChangeDataVersionCommand.create(wfm, version)  # also notifies client
    else:
        # no new data version, but we still want client to update WfModule status and last update check time
        notify_client_workflow_version_changed(wfm.workflow)
