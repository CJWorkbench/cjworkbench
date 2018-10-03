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


async def WorkflowUndo(workflow):
    """Run workflow.last_delta, backwards."""
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    delta = workflow.last_delta

    # Undo, if not at the very beginning of undo chain
    if delta:
        # Make sure delta.backward() edits the passed `workflow` argument.
        delta.workflow = workflow
        await delta.backward()  # uses cooperative lock


async def WorkflowRedo(workflow):
    """Run workflow.last_delta.next_delta, forward."""
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    if workflow.last_delta:
        delta = workflow.last_delta.next_delta
    else:
        # we are at very beginning of delta chain; find first delta
        delta = workflow.deltas.filter(prev_delta__isnull=True).first()

    # Redo, if not at very end of undo chain
    if delta:
        # Make sure delta.forward() edits the passed `workflow` argument.
        delta.workflow = workflow
        await delta.forward()


async def save_result_if_changed(
    wfm: WfModule,
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
        # clears error for good fetch after bad #160367251
        # TODO why not simply call render()?
        wfm.cached_render_result_error = new_result.error
        wfm.save()

        # Mark has_unseen_notifications via direct SQL
        WfModule.objects \
            .filter(id__in=[od.wf_module_id for od in output_deltas]) \
            .update(has_unseen_notification=True)

    # un-indent: COMMIT so we notify the client _after_ COMMIT
    if version_added:
        # notifies client
        await ChangeDataVersionCommand.create(wfm, version_added)

        for output_delta in output_deltas:
            email_output_delta(output_delta, version_added)
    else:
        # no new data version, but we still want client to update WfModule
        # status and last update check time
        # TODO why not just send WfModule?
        await websockets.ws_client_rerender_workflow_async(wfm.workflow)

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
