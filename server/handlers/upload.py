import functools
import uuid as uuidgen
from typing import Any, Dict

from django.conf import settings

from cjworkbench.sync import database_sync_to_async
from cjwstate import clientside, rabbitmq, upload
from cjwstate.models import Step, Workflow
from cjwstate.models.uploaded_file import delete_old_files_to_enforce_storage_limits
from server import serializers
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


@database_sync_to_async
def _load_step(workflow: Workflow, step_slug: str) -> Step:
    """Return a Step or raise HandlerError."""
    try:
        with upload.locked_and_loaded_step(workflow.id, step_slug) as (_, step, __):
            pass
    except upload.UploadError as err:
        raise HandlerError("UploadError: %s" % err.error_code)
    return step


def _loading_step(func):
    @functools.wraps(func)
    async def inner(workflow: Workflow, stepSlug: str, **kwargs):
        step = await _load_step(workflow, str(stepSlug))
        return await func(workflow=workflow, step=step, **kwargs)

    return inner


@register_websockets_handler
@websockets_handler("write")
@_loading_step
async def create_upload(
    workflow: Workflow, step: Step, filename: str, size: int, **kwargs
):
    """Prepare a file for the caller to upload to."""
    filename = str(filename)
    size = int(size)
    if len(filename) < 0 or len(filename) > 100:
        raise HandlerError("filename must be between 0 and 100 characters long")
    if size < 0 or size > settings.MINIO_MAX_FILE_SIZE:
        raise HandlerError(
            f"file size must be between 0 and {settings.MINIO_MAX_FILE_SIZE} bytes"
        )

    tus_upload_url = await upload.create_tus_upload(
        workflow_id=workflow.id,
        step_slug=step.slug,
        api_token="",
        filename=filename,
        size=size,
    )
    return {"tusUploadUrl": tus_upload_url}
