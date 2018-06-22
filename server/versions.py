# Undo, redo, and other version related things
import datetime
from django.utils import timezone
from django.conf import settings
from pandas import DataFrame
from server.models import Delta, Workflow, WfModule
from server.models import ChangeDataVersionCommand, StoredObject
from server.notifications import find_output_deltas_to_notify_from_fetched_tables, email_output_delta
from server.triggerrender import notify_client_workflow_version_changed


# Undo is pretty much just running workflow.last_delta backwards
def WorkflowUndo(workflow):
    with workflow.cooperative_lock():
        delta = workflow.last_delta

        # Undo, if not at the very beginning of undo chain
        if delta:
            delta.backward()
            workflow.refresh_from_db() # backward() may change it
            workflow.last_delta = delta.prev_delta
            workflow.save()

    # oh, also update the version, and notify the client (after COMMIT)
    notify_client_workflow_version_changed(workflow)


# Redo is pretty much just running workflow.last_delta.next_delta forward
def WorkflowRedo(workflow):
    with workflow.cooperative_lock():
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

    # oh, also update the version, and notify the client (after COMMIT)
    notify_client_workflow_version_changed(workflow)


def save_fetched_table_if_changed(wfm: WfModule, new_table: DataFrame,
                                  error_message: str) -> datetime.datetime:
    """Store retrieved data table, if it is a change from wfm's existing data.

    "Change" here means either a changed table or changed error message.
    
    The WfModule's `status` and `error_msg` will be set, according to
    `error_message`.

    Set wfm.last_update_check, regardless.

    Create (and run) a ChangeDataVersionCommand.

    Notify the user.

    Return the timestamp (if changed) or None (if not).
    """

    with wfm.workflow.cooperative_lock():
        wfm.last_update_check = timezone.now()

        # Store this data only if it's different from most recent data
        old_table = wfm.retrieve_fetched_table()
        version_added = wfm.store_fetched_table_if_different(new_table)

        if version_added:
            enforce_storage_limits(wfm)

            output_deltas = \
                    find_output_deltas_to_notify_from_fetched_tables(wfm,
                                                                   old_table,
                                                                   new_table)
        else:
            output_deltas = []

        wfm.has_unseen_notification = bool(output_deltas)
        wfm.error_msg = error_message or ''
        wfm.status = (WfModule.ERROR if error_message else WfModule.READY)
        wfm.save()

    # un-indent: COMMIT, so we can notify the client and the client sees changes
    if version_added:
        ChangeDataVersionCommand.create(wfm, version_added)  # also notifies client

        for output_delta in output_deltas:
            email_output_delta(output_delta)
    else:
        # no new data version, but we still want client to update WfModule status and last update check time
        notify_client_workflow_version_changed(wfm.workflow)

    return version_added


# Ensures that no one WfModule can suck up too much disk space, by deleting old versions
# This is a problem with frequently updating modules that add to the previous table, e.g. Twitter search,
# because we store whole files and not just deltas.
def enforce_storage_limits(wfm):
    limit = settings.MAX_STORAGE_PER_MODULE

    # walk over this WfM's StoredObjects from newest to oldest, deleting all that are over the limit
    sos = StoredObject.objects.filter(wf_module=wfm).order_by('-stored_at')
    cumulative = 0
    first = True

    for so in sos:
        cumulative += so.size
        if cumulative > limit and not first:  # allow most recent version to be stored even if it is itself over limit
            so.delete()
        first = False
