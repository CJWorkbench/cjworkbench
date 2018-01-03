# Undo, redo, and other version related things
from server.models import Delta, Workflow
from server.websockets import *
from server.models import ChangeDataVersionCommand, Notification
from server.triggerrender import notify_client_workflow_version_changed
from django.utils import timezone

# Undo is pretty much just running workflow.last_delta backwards
def WorkflowUndo(workflow):
    delta = workflow.last_delta

    # Undo, if not at the very beginning of undo chain
    if delta:
        delta.backward()
        workflow.refresh_from_db() # backward() may change it
        workflow.last_delta = delta.prev_delta
        workflow.save()

        # oh, also update the version, and notify the client
        notify_client_workflow_version_changed(workflow)


# Redo is pretty much just running workflow.last_delta.next_delta forward
def WorkflowRedo(workflow):

    # if we are at very beginning of delta chain, find first delta from db
    if workflow.last_delta:
        next_delta = workflow.last_delta.next_delta
    else:
        next_delta = Delta.objects.filter(workflow=workflow).order_by('datetime').first()

    # Redo, if not at very end of undo chain
    if next_delta:
        next_delta.forward()
        workflow.refresh_from_db() # forward() may change it
        workflow.last_delta = next_delta
        workflow.save()

        # oh, also update the version, and notify the client
        notify_client_workflow_version_changed(workflow)


# Store retrieved data (in text form here, as csv) if it isn't different from currently stored data
# If it is and auto_change_verssion, switch to new data using a ChangeDataVersion command
def save_fetched_table_if_changed(wfm, new_table, auto_change_version=True):

    wfm.last_update_check = timezone.now()
    wfm.save()

    # Store this data only if it's different from most recent data
    version_added = wfm.store_fetched_table_if_different(new_table)

    if version_added and auto_change_version:
        if wfm.notifications == True:
            Notification.create(wfm, "New data version available")
        if auto_change_version:
            ChangeDataVersionCommand.create(wfm, version_added)  # also notifies client
    else:
        # no new data version, but we still want client to update WfModule status and last update check time
        notify_client_workflow_version_changed(wfm.workflow)
