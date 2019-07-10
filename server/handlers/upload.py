import functools
from pathlib import PurePath
from typing import Any, Dict, List, Tuple, Union
import uuid as uuidgen
import urllib.parse
from django.utils import timezone
from cjworkbench.sync import database_sync_to_async
from server.models import UploadedFile, Workflow, WfModule
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


def _loading_wf_module_with_upload(func):
    """
    Set `wf_module` and `upload_id`, and guard against incorrect `uploadId`.

    There are some annoying races in this module, because
    [2019-05-30, adamhooper] I'm lazy. Ideally, we'd lock the workflow so
    concurrent requests read+write `wf_module.inprogress_file_upload_*` in
    serial. But that's inconvenient to code: we can't just wrap the whole
    inner function in a transaction because we need to can only send a delta
    to Websockets listeners _after_ the transaction is committed.

    TODO Make workflow.cooperative_lock() use a pg_locker. Then we can write
    to the database without transactions and send deltas while the workflow
    is still locked; `_loading_wf_module` would lock as a matter of course.
    """

    @functools.wraps(func)
    async def inner(workflow: Workflow, wfModuleId: int, uploadId: str, **kwargs):
        uploadId = str(uploadId)  # ensure type
        wf_module = await _load_wf_module(workflow, wfModuleId)
        # security: only allow modifying _this_ WfModule's upload.
        if wf_module.inprogress_file_upload_id != uploadId:
            raise HandlerError("NoSuchUpload: uploadId is invalid")
        return await func(
            workflow=workflow, wf_module=wf_module, upload_id=uploadId, **kwargs
        )

    return inner


def _generate_key(wf_module: WfModule, filename: str) -> str:
    """
    Generate a key for where a file belongs on S3.

    The key includes all the info we need to derive the UUID later. It also
    uses the same suffix as `filename`, to aid debugging.

    Assumes we're in a database transaction.
    """
    uuid = uuidgen.uuid4()
    return "".join(
        [wf_module.uploaded_file_prefix, str(uuid), PurePath(filename).suffix]
    )


def _write_uploaded_file_and_clear_inprogress_file_upload(
    wf_module: WfModule
) -> UploadedFile:
    """
    Read metadata from S3; write it to a new UploadedFile; save `wf_module`.

    Raise FileNotFoundError if `wf_module.inprogress_file_upload_key is None`
    or the file does not exist on minio.

    Assumptions:

    * You hold a cooperative lock on `wf_module.workflow`.
    * The client PUT a sensible Content-Disposition header. (Failure means icky
      filename, not crash.)
    """
    key = wf_module.inprogress_file_upload_key
    uuid: str = key.split("/")[-1].split(".")[0]
    # TODO raise FileNotFoundError
    head = minio.client.head_object(Bucket=minio.UserFilesBucket, Key=key)
    size = int(head["ContentLength"])
    name = urllib.parse.unquote(head["ContentDisposition"].split("UTF-8''")[-1])

    uploaded_file = wf_module.uploaded_files.create(
        name=name, size=size, uuid=uuid, bucket=minio.UserFilesBucket, key=key
    )

    wf_module.inprogress_file_upload_id = None
    wf_module.inprogress_file_upload_key = None
    wf_module.inprogress_file_upload_last_accessed_at = None
    wf_module.save(
        update_fields=[
            "inprogress_file_upload_id",
            "inprogress_file_upload_key",
            "inprogress_file_upload_last_accessed_at",
        ]
    )
    return uploaded_file


@database_sync_to_async
def _do_prepare_upload(
    workflow: Workflow,
    wf_module: WfModule,
    filename: str,
    n_bytes: int,
    base64Md5sum: str,
) -> Dict[str, str]:
    key = _generate_key(wf_module, filename)
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        wf_module.abort_inprogress_upload()

        url, headers = minio.presign_upload(
            minio.UserFilesBucket, key, filename, n_bytes, base64Md5sum
        )
        wf_module.inprogress_file_upload_id = None
        wf_module.inprogress_file_upload_key = key
        wf_module.inprogress_file_upload_last_accessed_at = timezone.now()
        wf_module.save(
            update_fields=[
                "inprogress_file_upload_id",
                "inprogress_file_upload_key",
                "inprogress_file_upload_last_accessed_at",
            ]
        )

    return {"key": key, "url": url, "headers": headers}


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def prepare_upload(
    workflow: Workflow,
    wf_module: WfModule,
    filename: str,
    nBytes: int,
    base64Md5sum: str,
    **kwargs
) -> Dict[str, Union[str, Dict[str, str]]]:
    """
    Build {key, url, headers} for the client.

    The client can PUT data to `url` with `headers`, and that will create `key`
    on S3. Upon success, the client should `complete_upload(key)`.
    """
    if not isinstance(filename, str):
        raise HandlerError("BadRequest: filename must be str")
    if not isinstance(nBytes, int) or nBytes < 0:
        raise HandlerError("BadRequest: nBytes must be positive int")
    if not isinstance(base64Md5sum, str):
        raise HandlerError("BadRequest: base64Md5sum must be str")
    return await _do_prepare_upload(workflow, wf_module, filename, nBytes, base64Md5sum)


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

    Set `wf_module.inprogress_file_upload_id`,
    `wf_module.inprogress_file_upload_key` and
    `wf_module.inprogress_file_upload_last_accessed_at` to `None`.

    Do nothing if the file upload is not for `wf_module`.
    """
    if wf_module.inprogress_file_upload_key is None:
        return  # no-op

    if wf_module.inprogress_file_upload_key != key:
        raise HandlerError("NoSuchUpload: the key you provided is not being uploaded")

    await _do_abort_upload(wf_module)


@database_sync_to_async
def _do_complete_upload(
    workflow: Workflow, wf_module: WfModule, key: str
) -> Tuple[UploadedFile, Dict[str, Any]]:
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        if (
            wf_module.inprogress_file_upload_id is not None
            or wf_module.inprogress_file_upload_key != key
        ):
            raise HandlerError("DoesNotExist: key must point to an incomplete upload")
        uploaded_file = _write_uploaded_file_and_clear_inprogress_file_upload(wf_module)
        return (uploaded_file.uuid, serializers.WfModuleSerializer(wf_module).data)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def complete_upload(workflow: Workflow, wf_module: WfModule, key: str, **kwargs):
    if not isinstance(key, str):
        raise HandlerError("BadRequest: key must be str")
    uuid, wf_module_data = await _do_complete_upload(workflow, wf_module, key)
    await websockets.ws_client_send_delta_async(
        workflow.id, {"updateWfModules": {str(wf_module.id): wf_module_data}}
    )
    return {"uuid": uuid}


@database_sync_to_async
def _do_create_multipart_upload(
    workflow: Workflow, wf_module: WfModule, filename: str
) -> Dict[str, str]:
    key = _generate_key(wf_module, filename)
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        wf_module.abort_inprogress_upload()  # in case there is one already

        upload_id = minio.create_multipart_upload(minio.UserFilesBucket, key, filename)
        wf_module.inprogress_file_upload_id = upload_id
        wf_module.inprogress_file_upload_key = key
        wf_module.inprogress_file_upload_last_accessed_at = timezone.now()
        wf_module.save(
            update_fields=[
                "inprogress_file_upload_id",
                "inprogress_file_upload_key",
                "inprogress_file_upload_last_accessed_at",
            ]
        )

    return {"key": key, "uploadId": upload_id}


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module
async def create_multipart_upload(
    workflow: Workflow, wf_module: WfModule, filename: str, **kwargs
):
    """
    Initiate a multipart file upload for `wf_module`.

    Set `wf_module.inprogress_file_upload_id`,
    `wf_module.inprogress_file_upload_key` and
    `wf_module.inprogress_file_upload_last_accessed_at`. Return
    `{ key, uploadId }` for the client.
    """
    if not isinstance(filename, str):
        raise HandlerError("BadRequest: filename must be str")
    return await _do_create_multipart_upload(workflow, wf_module, filename)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module_with_upload
async def abort_multipart_upload(
    workflow: Workflow, wf_module: WfModule, upload_id: str, **kwargs
) -> None:
    """
    Delete all resources associated with a multipart file upload.

    Set `wf_module.inprogress_file_upload_id`,
    `wf_module.inprogress_file_upload_key` and
    `wf_module.inprogress_file_upload_last_accessed_at` to `None`.

    Do nothing if the multipart file upload is not for `wf_module`.
    """
    await _do_abort_upload(wf_module)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module_with_upload
async def presign_upload_part(
    workflow: Workflow,
    wf_module: WfModule,
    upload_id: str,
    partNumber: int,
    nBytes: int,
    base64Md5sum: str,
    **kwargs
):
    """
    Build { url, headers } Object for caller to PUT bytes to.

    The caller must PUT using exactly the headers provided. Changes in url,
    headers or body will be rejected by S3.

    The caller must validate S3's response when it PUTs. It must also remember
    the `ETag` header value from S3's response. The `ETag` header is quirky
    because it's surrounded by quotation marks; the caller must remove those
    quotes. (ETags are needed by `complete_multipart_upload()`.)
    """
    if not isinstance(partNumber, int) or partNumber < 1:
        raise HandlerError("BadRequest: partNumber must be int >= 1")
    if not isinstance(nBytes, int) or nBytes < 0:
        raise HandlerError("BadRequest: nBytes must be positive integer")
    if not isinstance(base64Md5sum, str):
        raise HandlerError("BadRequest: base64Md5sum must be str")
    url, headers = minio.presign_upload_part(
        minio.UserFilesBucket,
        wf_module.inprogress_file_upload_key,
        upload_id,
        partNumber,
        nBytes,
        base64Md5sum,
    )
    return dict(url=url, headers=headers)


@database_sync_to_async
def _do_complete_multipart_upload(
    workflow: Workflow, wf_module: WfModule
) -> Tuple[UploadedFile, Dict[str, Any]]:
    with workflow.cooperative_lock():
        wf_module.refresh_from_db()
        uploaded_file = _write_uploaded_file_and_clear_inprogress_file_upload(wf_module)
        return (uploaded_file.uuid, serializers.WfModuleSerializer(wf_module).data)


@register_websockets_handler
@websockets_handler("write")
@_loading_wf_module_with_upload
async def complete_multipart_upload(
    workflow: Workflow, wf_module: WfModule, upload_id: str, etags: List[str], **kwargs
):
    """
    Complete a multipart upload; create an UploadedFile; send a Delta.

    Set `wf_module.inprogress_file_upload_id`,
    `wf_module.inprogress_file_upload_key` and
    `wf_module.inprogress_file_upload_last_accessed_at` to `None`.
    """
    if not isinstance(etags, list) or any(not isinstance(etag, str) for etag in etags):
        raise HandlerError("BadRequest: etags must be List[str]")
    key = wf_module.inprogress_file_upload_key
    minio.complete_multipart_upload(minio.UserFilesBucket, key, upload_id, etags)

    uuid, wf_module_data = await _do_complete_multipart_upload(workflow, wf_module)

    await websockets.ws_client_send_delta_async(
        workflow.id, {"updateWfModules": {str(wf_module.id): wf_module_data}}
    )

    return {"uuid": uuid}
