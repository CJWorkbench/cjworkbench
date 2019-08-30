from typing import Optional
from django.utils import timezone
import pandas as pd
from cjworkbench.sync import database_sync_to_async
from cjwkernel.pandas.types import ProcessResult
from cjwstate import storedobjects
from server import websockets
from cjwstate.models import WfModule, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand


def _store_fetched_table_if_different(
    workflow: Workflow, wf_module: WfModule, table: pd.DataFrame
) -> Optional[timezone.datetime]:
    # Called within _maybe_add_version()
    hash = storedobjects.hash_table(table)
    old_so = wf_module.stored_objects.order_by("-stored_at").first()
    if (
        old_so is not None
        # Fast: hashes differ, so we don't need to read the table
        and hash == old_so.hash
        # Slow: compare files. Expensive: reads a file from S3, holds
        # both DataFrames in RAM, uses lots of CPU.
        and table.equals(storedobjects.read_dataframe_from_stored_object(old_so))
    ):
        # `table` is identical to what was in `old_so`.
        return None

    stored_object = storedobjects.create_stored_object(workflow, wf_module, table, hash)
    storedobjects.enforce_storage_limits(wf_module)
    return stored_object.stored_at


@database_sync_to_async
def _maybe_add_version(
    workflow: Workflow, wf_module: WfModule, maybe_result: Optional[ProcessResult]
) -> Optional[timezone.datetime]:
    """
    Apply `result` to `wf_module`.

    Set `is_busy`, `fetch_error` and `last_update_check`.

    Write a new `StoredObject` and returns its `datetime` if the input
    `maybe_result` is non-``None`` and the result isn't the same as the
    previous one. Che caller may create a ``ChangeDataVersionCommand`` to set
    `wf_module`'s next data version.

    If the input Workflow or WfModule is deleted, return ``None``.
    """
    # Use Django `update_fields` to only write the fields we're
    # editing.  That's because every value in `wf_module` might be
    # stale, so we must ignore those stale values.
    fields = {"is_busy": False, "last_update_check": timezone.now()}
    if maybe_result is not None:
        fields["fetch_error"] = maybe_result.error

    for k, v in fields.items():
        setattr(wf_module, k, v)

    try:
        with wf_module.workflow.cooperative_lock():
            if not WfModule.objects.filter(
                pk=wf_module.id, is_deleted=False, tab__is_deleted=False
            ).exists():
                return None

            if maybe_result is not None:
                # TODO store result error, too. Actually, nix StoredObject
                # entirely and let fetch methods return arbitrary blobs.
                version_added = _store_fetched_table_if_different(
                    workflow, wf_module, maybe_result.dataframe
                )
            else:
                version_added = None

            wf_module.save(update_fields=fields.keys())

            return version_added
    except Workflow.DoesNotExist:
        return None


@database_sync_to_async
def get_wf_module_workflow(wf_module: WfModule) -> Workflow:
    return wf_module.workflow  # does a database query


async def save_result_if_changed(
    workflow_id: int, wf_module: WfModule, new_result: Optional[ProcessResult]
) -> None:
    """
    Store fetched table, if it is a change from `wf_module`'s existing data.

    "Change" here means either a changed table or changed error message.

    Set `fetch_error` to `new_result.error`.

    Set wf_module.is_busy to False.

    Set wf_module.last_update_check.

    Create (and run) a ChangeDataVersionCommand if something changed. This
    will kick off an execute cycle, which will render each module and email the
    owner if data has changed and notifications are enabled.

    Otherwise, notify the user of the wf_module.last_update_check.

    Call with `new_result=None` to indicate that a fetch is finished and
    guarantee not to add a new version.
    """
    try:
        workflow = await get_wf_module_workflow(wf_module)
    except Workflow.DoesNotExist:
        return  # there's nothing more to do

    version_added = await _maybe_add_version(workflow, wf_module, new_result)

    if version_added:
        # Don't send_delta_async. wf_module.last_relevant_delta_id hasn't been
        # set, so at this point the module would appear to be "ready". (See
        # https://www.pivotaltracker.com/story/show/161863167 for an example.)
        # Instead, trust ChangeDataVersionCommand to update `is_busy` and
        # `fetch_error`.
        #
        # Rephrased:
        #
        # * Right here, the user sees "busy" (is_busy=True, cache=fresh)
        # * After the next line of code, the user _still_sees "busy"
        #   (is_busy=False, cache=stale)
        # * Later, the user will see "ok" (is_busy=False, cache=fresh)
        await ChangeDataVersionCommand.create(
            workflow=workflow, wf_module=wf_module, new_version=version_added
        )
    else:
        last_update_check = wf_module.last_update_check
        if last_update_check:
            last_update_check = last_update_check.isoformat()

        await websockets.ws_client_send_delta_async(
            workflow_id,
            {
                "updateWfModules": {
                    str(wf_module.id): {
                        "is_busy": wf_module.is_busy,
                        "fetch_error": wf_module.fetch_error,
                        "last_update_check": last_update_check,
                    }
                }
            },
        )
