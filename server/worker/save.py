import json
from typing import Any, Dict, Optional
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone
from server import websockets
from server.models import WfModule, Workflow
from server.models.commands import ChangeDataVersionCommand
from server.modules.types import ProcessResult


@database_sync_to_async
def _maybe_add_version(
    wf_module: WfModule,
    maybe_result: Optional[ProcessResult],
    stored_object_json: Optional[Dict[str, Any]]=None
) -> Optional[timezone.datetime]:
    """
    Apply `result` to `wf_module`.

    Set `is_busy`, `fetch_error` and `last_update_check`.

    Write a new `StoredObject` and returns its `datetime` if the input
    `maybe_result` is non-``None`` and the result isn't the same as the
    previous one. Che caller may create a ``ChangeDataVersionCommand`` to set
    `wf_module`'s next data version.
    """
    try:
        workflow = wf_module.workflow
    except Workflow.DoesNotExist:
        return None

    with workflow.cooperative_lock():
        # Use Django `update_fields` to only write the fields we're editing.
        # That's because every value in `wf_module` might be stale, so we must
        # ignore those stale values.
        fields = {
            'is_busy': False,
            'last_update_check': timezone.now(),
        }
        if maybe_result is not None:
            fields['fetch_error'] = maybe_result.error

            version_added = wf_module.store_fetched_table_if_different(
                maybe_result.dataframe,  # TODO store entire result
                metadata=json.dumps(stored_object_json)
            )
        else:
            version_added = None

        if version_added:
            enforce_storage_limits(wf_module)

        for k, v in fields.items():
            setattr(wf_module, k, v)
        wf_module.save(update_fields=fields.keys())

        return version_added


async def save_result_if_changed(
    wf_module: WfModule,
    new_result: Optional[ProcessResult],
    stored_object_json: Optional[Dict[str, Any]]=None
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
    version_added = await _maybe_add_version(wf_module, new_result,
                                             stored_object_json)

    # un-indent: COMMIT so we notify the client _after_ COMMIT
    if version_added:
        # notifies client of status+error_msg+last_update_check
        await ChangeDataVersionCommand.create(wf_module, version_added)
    else:
        await websockets.ws_client_send_delta_async(wf_module.workflow_id, {
            'updateWfModules': {
                str(wf_module.id): {
                    'status': wf_module.status,
                    'error_msg': wf_module.error_msg,
                    'last_update_check': (
                        wf_module.last_update_check.isoformat()
                    ),
                }
            }
        })


def enforce_storage_limits(wf_module: WfModule) -> None:
    """
    Delete old versions that bring us past MAX_STORAGE_PER_MODULE.

    This is important on frequently-updating modules that add to the previous
    table, such as Twitter search, because every version we store is an entire
    table. Without deleting old versions, we'd grow too quickly.
    """
    limit = settings.MAX_STORAGE_PER_MODULE

    # walk over this WfM's StoredObjects from newest to oldest, deleting all
    # that are over the limit
    sos = wf_module.stored_objects.order_by('-stored_at')
    cumulative = 0
    first = True

    for so in sos:
        cumulative += so.size
        if cumulative > limit and not first:
            # allow most recent version to be stored even if it is itself over
            # limit
            so.delete()
        first = False
