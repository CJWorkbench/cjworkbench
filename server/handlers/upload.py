import functools
from pathlib import PurePath
from typing import Any, Dict
import uuid as uuidgen
from django.conf import settings
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from server.models import Workflow, WfModule
from server import minio, serializers, websockets
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


def _generate_upload_key(wf_module: WfModule) -> str:
    """
    Generate a key for where an upload belongs on S3, before Workbench sees it.

    The key includes all the info we need to derive the UUID later. It looks like
    'wf-123/wfm-234/upload_UUID'

    Assumes we're in a database transaction.
    """
    uuid = uuidgen.uuid4()
    return wf_module.uploaded_file_prefix + "upload_" + str(uuid)


@database_sync_to_async
def _do_abort_upload(wf_module: WfModule) -> None:
    wf_module.abort_inprogress_upload()


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def abort_upload(
    workflow: Workflow, wf_module: WfModule, key: str, **kwargs
) -> None:
    """
    Delete all resources associated with a file upload.

    Set `wf_module.inprogress_file_upload_key` and
    `wf_module.inprogress_file_upload_last_accessed_at` to `None`.

    Do nothing if the file upload is not for `wf_module`.
    """
    if wf_module.inprogress_file_upload_key is None:
        return  # no-op

    if wf_module.inprogress_file_upload_key != key:
        raise HandlerError("NoSuchUpload: the key you provided is not being uploaded")

    await _do_abort_upload(wf_module)


@database_sync_to_async
def _do_create_upload(workflow: Workflow, wf_module: WfModule) -> Dict[str, Any]:
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        key = _generate_upload_key(wf_module)
        credentials = minio.assume_role_to_write(minio.UserFilesBucket, key)
        wf_module.abort_inprogress_upload()
        wf_module.inprogress_file_upload_key = key
        wf_module.inprogress_file_upload_last_accessed_at = timezone.now()
        wf_module.save(
            update_fields=[
                "inprogress_file_upload_key",
                "inprogress_file_upload_last_accessed_at",
            ]
        )
        return {
            "endpoint": settings.MINIO_EXTERNAL_URL,
            "region": "us-east-1",
            "bucket": minio.UserFilesBucket,
            "key": key,
            "credentials": credentials,
        }


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def create_upload(workflow: Workflow, wf_module: WfModule, **kwargs):
    """
    Prepare credentials for the caller to upload a file.

    Beware: the credentials let the caller upload to S3 to the returned
    key for the next few hours. We can't trust callers to not upload even when
    they aren't supposed to. TODO track these keys in the database, so we
    force-abort (and force-delete) spurious uploads after 5h.
    """
    return await _do_create_upload(workflow, wf_module)


@database_sync_to_async
def _do_finish_upload(workflow: Workflow, wf_module: WfModule, key: str, filename: str):
    suffix = PurePath(filename).suffix
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        if key != wf_module.inprogress_file_upload_key:
            raise HandlerError(
                "BadRequest: key is not being uploaded for this WfModule right now. "
                "(Even a valid key becomes invalid after you create, finish or abort "
                "an upload on its WfModule.)"
            )
        prefix, uuid = key.split("upload_")
        final_key = prefix + uuid + suffix
        try:
            minio.copy(
                minio.UserFilesBucket,
                final_key,
                f"{minio.UserFilesBucket}/{key}",
                ACL="private",
                MetadataDirective="REPLACE",
                ContentDisposition=minio.encode_content_disposition(filename),
                ContentType="application/octet-stream",
            )
        except minio.error.NoSuchKey:
            raise HandlerError(
                "BadRequest: file not found. "
                "You must upload the file before calling finish_upload."
            )
        size = minio.stat(minio.UserFilesBucket, final_key).size
        # Point to the new file
        wf_module.uploaded_files.create(
            name=filename,
            size=size,
            uuid=uuid,
            bucket=minio.UserFilesBucket,
            key=final_key,
        )
        wf_module.abort_inprogress_upload()  # clear all tempfiles and temp DB fields
        return uuid, serializers.WfModuleSerializer(wf_module).data


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def finish_upload(
    workflow: Workflow, wf_module: WfModule, key: str, filename: str, **kwargs
):
    uuid, wf_module_data = await _do_finish_upload(workflow, wf_module, key, filename)
    await websockets.ws_client_send_delta_async(
        workflow.id, {"updateWfModules": {str(wf_module.id): wf_module_data}}
    )
    return {"uuid": uuid}
