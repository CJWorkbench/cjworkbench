# Undo, redo, and other version related things
import datetime
import json
from typing import Optional, Dict, Any
from django.utils import timezone
from django.conf import settings
from server.models import Delta, WfModule
from server.models import ChangeDataVersionCommand, StoredObject
from server.modules.types import ProcessResult
from server.notifications import \
        find_output_deltas_to_notify_from_fetched_tables, email_output_delta
from server import websockets


# Undo is pretty much just running workflow.last_delta backwards
def WorkflowUndo(workflow):
    with workflow.cooperative_lock():
        delta = workflow.last_delta

        # Undo, if not at the very beginning of undo chain
        if delta:
            delta.backward()
            workflow.refresh_from_db()  # backward() may change it
            workflow.last_delta = delta.prev_delta
            workflow.save()


# Redo is pretty much just running workflow.last_delta.next_delta forward
def WorkflowRedo(workflow):
    with workflow.cooperative_lock():
        # if we are at very beginning of delta chain, find first delta from db
        if workflow.last_delta:
            next_delta = workflow.last_delta.next_delta
        else:
            next_delta = Delta.objects.filter(workflow=workflow) \
                    .order_by('datetime').first()

        # Redo, if not at very end of undo chain
        if next_delta:
            next_delta.forward()
            workflow.refresh_from_db()  # forward() may change it
            workflow.last_delta = next_delta
            workflow.save()


def save_result_if_changed(wfm: WfModule,
                           new_result: ProcessResult,
                           stored_object_json: Optional[Dict[str, Any]]=None
                           ) -> datetime.datetime:
    """
    Store fetched table, if it is a change from wfm's existing data.

    "Change" here means either a changed table or changed error message.

    Set `fetch_error` to `new_result.error`.

    Set sfm.is_busy to False.

    Set wfm.last_update_check.

    Create (and run) a ChangeDataVersionCommand.

    Notify the user.

    Return the timestamp (if changed) or None (if not).
    """
    with wfm.workflow.cooperative_lock():
        wfm.last_update_check = timezone.now()

        # Store this data only if it's different from most recent data
        old_result = ProcessResult(
            dataframe=wfm.retrieve_fetched_table(),
            error=wfm.error_msg
        )
        new_table = new_result.dataframe
        version_added = wfm.store_fetched_table_if_different(
            new_table,
            metadata=json.dumps(stored_object_json)
        )

        if version_added:
            enforce_storage_limits(wfm)

            output_deltas = \
                find_output_deltas_to_notify_from_fetched_tables(wfm,
                                                                 old_result,
                                                                 new_result)
        else:
            output_deltas = []

        wfm.is_busy = False
        wfm.fetch_error = new_result.error
        wfm.save()

        # Mark has_unseen_notifications via direct SQL
        WfModule.objects \
            .filter(id__in=[od.wf_module_id for od in output_deltas]) \
            .update(has_unseen_notification=True)

    # un-indent: COMMIT so we notify the client _after_ COMMIT
    if version_added:
        ChangeDataVersionCommand.create(wfm, version_added)  # notifies client

        for output_delta in output_deltas:
            email_output_delta(output_delta, version_added)
    else:
        # no new data version, but we still want client to update WfModule
        # status and last update check time
        websockets.ws_client_rerender_workflow(wfm.workflow)

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
