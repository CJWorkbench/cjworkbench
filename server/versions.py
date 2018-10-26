# Undo, redo, and other version related things
import json
from typing import Optional, Dict, Any
from django.utils import timezone
from django.conf import settings
from server.models import StoredObject, WfModule
from server.models.commands import ChangeDataVersionCommand
from server.modules.types import ProcessResult
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
) -> None:
    """
    Store fetched table, if it is a change from wfm's existing data.

    "Change" here means either a changed table or changed error message.

    Set `fetch_error` to `new_result.error`.

    Set wfm.is_busy to False.

    Set wfm.last_update_check.

    Create (and run) a ChangeDataVersionCommand if something changed. This
    will kick off an execute cycle, which will render each module and email the
    owner if data has changed and notifications are enabled.

    Otherwise, notify the user of the wfm.last_update_check.

    Return the timestamp (if changed) or None (if not).
    """
    with wfm.workflow.cooperative_lock():
        wfm.last_update_check = timezone.now()

        # Store this data only if it's different from most recent data
        new_table = new_result.dataframe
        version_added = wfm.store_fetched_table_if_different(
            new_table,
            metadata=json.dumps(stored_object_json)
        )

        if version_added:
            enforce_storage_limits(wfm)

        wfm.is_busy = False
        # TODO store fetch_error along with the data
        wfm.fetch_error = new_result.error
        wfm.save()

    # un-indent: COMMIT so we notify the client _after_ COMMIT
    if version_added:
        # notifies client of status+error_msg+last_update_check
        await ChangeDataVersionCommand.create(wfm, version_added)
    else:
        await websockets.ws_client_send_delta_async(wfm.workflow_id, {
            'updateWfModules': {
                str(wfm.id): {
                    'status': wfm.status,
                    'error_msg': wfm.error_msg,
                    'last_update_check': wfm.last_update_check.isoformat(),
                }
            }
        })


def enforce_storage_limits(wfm):
    """
    Delete old versions that bring us past MAX_STORAGE_PER_MODULE.

    This is important on frequently-updating modules that add to the previous
    table, such as Twitter search, because every version we store is an entire
    table. Without deleting old versions, we'd grow too quickly.
    """
    limit = settings.MAX_STORAGE_PER_MODULE

    # walk over this WfM's StoredObjects from newest to oldest, deleting all
    # that are over the limit
    sos = StoredObject.objects.filter(wf_module=wfm).order_by('-stored_at')
    cumulative = 0
    first = True

    for so in sos:
        cumulative += so.size
        if cumulative > limit and not first:
            # allow most recent version to be stored even if it is itself over
            # limit
            so.delete()
        first = False
