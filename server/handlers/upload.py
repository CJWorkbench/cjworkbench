import functools
from typing import Any, Dict
import uuid as uuidgen
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow, WfModule, InProgressUpload
from server import serializers
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


@database_sync_to_async
def _load_wf_module(workflow: Workflow, wf_module_id: int) -> WfModule:
    """Returns a WfModule or raises HandlerError."""
    try:
        return WfModule.live_in_workflow(workflow).get(id=wf_module_id)
    except WfModule.DoesNotExist:
        raise HandlerError("DoesNotExist: WfModule not found")


def _loading_wf_module(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, wfModuleId: int, **kwargs):
        wf_module = await _load_wf_module(workflow, wfModuleId)
        return await func(workflow=workflow, wf_module=wf_module, **kwargs)

    return inner


@database_sync_to_async
def _do_abort_upload(
    workflow: Workflow, wf_module: WfModule, uuid: uuidgen.UUID
) -> None:
    with workflow.cooperative_lock():
        try:
            in_progress_upload = wf_module.in_progress_uploads.get(id=uuid)
        except InProgressUpload.DoesNotExist:
            return  # no-op
        in_progress_upload.delete_s3_data()
        # Aborted upload should disappear, as far as the user is concerned
        in_progress_upload.is_completed = True
        in_progress_upload.save(update_fields=["is_completed"])


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def abort_upload(
    workflow: Workflow, wf_module: WfModule, key: str, **kwargs
) -> None:
    """
    Delete all resources associated with an InProgressFileUpload.

    Do nothing if the file upload is not for `wf_module`.
    """
    try:
        uuid = InProgressUpload.upload_key_to_uuid(key)
    except ValueError as err:
        raise HandlerError(str(err))
    await _do_abort_upload(workflow, wf_module, uuid)


@database_sync_to_async
def _do_create_upload(workflow: Workflow, wf_module: WfModule) -> Dict[str, Any]:
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        in_progress_upload = wf_module.in_progress_uploads.create()
        return in_progress_upload.generate_upload_parameters()


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def create_upload(workflow: Workflow, wf_module: WfModule, **kwargs):
    """
    Prepare a key and credentials for the caller to upload a file.
    """
    result = await _do_create_upload(workflow, wf_module)
    result = {
        **result,
        "credentials": {
            **result["credentials"],
            "expiration": serializers.jsonize_datetime(
                result["credentials"]["expiration"]
            ),
        },
    }
    return result


@database_sync_to_async
def _do_finish_upload(
    workflow: Workflow, wf_module: WfModule, uuid: uuidgen.UUID, filename: str
) -> clientside.Update:
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        try:
            in_progress_upload = wf_module.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            raise HandlerError(
                "BadRequest: key is not being uploaded for this WfModule right now. "
                "(Even a valid key becomes invalid after you create, finish or abort "
                "an upload on its WfModule.)"
            )
        try:
            in_progress_upload.convert_to_uploaded_file(filename)
        except FileNotFoundError:
            raise HandlerError(
                "BadRequest: file not found. "
                "You must upload the file before calling finish_upload."
            )
        return clientside.Update(
            steps={
                wf_module.id: clientside.StepUpdate(
                    files=wf_module.to_clientside().files
                )
            }
        )


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def finish_upload(
    workflow: Workflow, wf_module: WfModule, key: str, filename: str, **kwargs
):
    try:
        uuid = InProgressUpload.upload_key_to_uuid(key)
    except ValueError as err:
        raise HandlerError(str(err))
    update = await _do_finish_upload(workflow, wf_module, uuid, filename)
    await rabbitmq.send_update_to_workflow_clients(workflow.id, update)
    return {"uuid": str(uuid)}
