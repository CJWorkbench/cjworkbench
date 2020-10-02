import functools
from typing import Any, Dict
import uuid as uuidgen
from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq
from cjwstate.models import Workflow, Step, InProgressUpload
from server import serializers
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


@database_sync_to_async
def _load_step(workflow: Workflow, step_id: int) -> Step:
    """Returns a Step or raises HandlerError."""
    try:
        return Step.live_in_workflow(workflow).get(id=step_id)
    except Step.DoesNotExist:
        raise HandlerError("DoesNotExist: Step not found")


def _loading_step(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, stepId: int, **kwargs):
        step = await _load_step(workflow, stepId)
        return await func(workflow=workflow, step=step, **kwargs)

    return inner


@database_sync_to_async
def _do_abort_upload(workflow: Workflow, step: Step, uuid: uuidgen.UUID) -> None:
    with workflow.cooperative_lock():
        try:
            in_progress_upload = step.in_progress_uploads.get(id=uuid)
        except InProgressUpload.DoesNotExist:
            return  # no-op
        in_progress_upload.delete_s3_data()
        # Aborted upload should disappear, as far as the user is concerned
        in_progress_upload.is_completed = True
        in_progress_upload.save(update_fields=["is_completed"])


@register_websockets_handler
@websockets_handler("write")
@_loading_step
async def abort_upload(workflow: Workflow, step: Step, key: str, **kwargs) -> None:
    """
    Delete all resources associated with an InProgressFileUpload.

    Do nothing if the file upload is not for `step`.
    """
    try:
        uuid = InProgressUpload.upload_key_to_uuid(key)
    except ValueError as err:
        raise HandlerError(str(err))
    await _do_abort_upload(workflow, step, uuid)


@database_sync_to_async
def _do_create_upload(workflow: Workflow, step: Step) -> Dict[str, Any]:
    with workflow.cooperative_lock():
        step.refresh_from_db()
        in_progress_upload = step.in_progress_uploads.create()
        return in_progress_upload.generate_upload_parameters()


@register_websockets_handler
@websockets_handler("write")
@_loading_step
async def create_upload(workflow: Workflow, step: Step, **kwargs):
    """Prepare a key and credentials for the caller to upload a file."""
    result = await _do_create_upload(workflow, step)
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
    workflow: Workflow, step: Step, uuid: uuidgen.UUID, filename: str
) -> clientside.Update:
    with workflow.cooperative_lock():
        step.refresh_from_db()
        try:
            in_progress_upload = step.in_progress_uploads.get(
                id=uuid, is_completed=False
            )
        except InProgressUpload.DoesNotExist:
            raise HandlerError(
                "BadRequest: key is not being uploaded for this Step right now. "
                "(Even a valid key becomes invalid after you create, finish or abort "
                "an upload on its Step.)"
            )
        try:
            in_progress_upload.convert_to_uploaded_file(filename)
        except FileNotFoundError:
            raise HandlerError(
                "BadRequest: file not found. "
                "You must upload the file before calling finish_upload."
            )
        return clientside.Update(
            steps={step.id: clientside.StepUpdate(files=step.to_clientside().files)}
        )


@register_websockets_handler
@websockets_handler("write")
@_loading_step
async def finish_upload(
    workflow: Workflow, step: Step, key: str, filename: str, **kwargs
):
    try:
        uuid = InProgressUpload.upload_key_to_uuid(key)
    except ValueError as err:
        raise HandlerError(str(err))
    update = await _do_finish_upload(workflow, step, uuid, filename)
    await rabbitmq.send_update_to_workflow_clients(workflow.id, update)
    return {"uuid": str(uuid)}
