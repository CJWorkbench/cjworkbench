from pathlib import Path
from typing import ContextManager, Optional
import uuid
from django.conf import settings
from django.utils import timezone
from cjwkernel.util import tempfile_context
from cjwstate import minio
from cjwstate.models import StoredObject, WfModule


BUCKET = minio.StoredObjectsBucket


def downloaded_file(stored_object: StoredObject, dir=None) -> ContextManager[Path]:
    """
    Context manager to download and yield `path`, the StoredObject's file.

    Raise FileNotFoundError if the object is missing.

    Usage:

        try:
            with storedobjects.downloaded_file(stored_object) as path:
                # do something with `path`, a `pathlib.Path`
        except FileNotFoundError:
            # file does not exist....
    """
    if stored_object.size == 0:
        # Some stored objects with size=0 do not have bucket/key. These are
        # valid -- they represent empty files.
        return tempfile_context(prefix="storedobjects-empty-file", dir=dir)
    else:
        # raises FileNotFoundError
        return minio.temporarily_download(
            minio.StoredObjectsBucket, stored_object.key, dir=dir
        )


def _build_key(workflow_id: int, wf_module_id: int) -> str:
    """Build a helpful S3 key."""
    return f"{workflow_id}/{wf_module_id}/{uuid.uuid1()}.dat"


def create_stored_object(
    workflow_id: int,
    wf_module_id: int,
    path: Path,
    stored_at: Optional[timezone.datetime] = None,
) -> StoredObject:
    """
    Write and return a new StoredObject.

    The caller should call enforce_storage_limits() after calling this.

    Raise IntegrityError if a database race prevents saving this. Raise a minio
    error if writing to minio failed. In case of partial completion, a
    StoredObject will exist in the database but no file will be saved in minio.
    """
    if stored_at is None:
        stored_at = timezone.now()
    key = _build_key(workflow_id, wf_module_id)
    size = path.stat().st_size
    stored_object = StoredObject.objects.create(
        stored_at=stored_at,
        wf_module_id=wf_module_id,
        bucket=BUCKET,
        key=key,
        size=size,
        hash="unhashed",
    )
    minio.fput_file(BUCKET, key, path)
    return stored_object


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
    sos = wf_module.stored_objects.order_by("-stored_at")
    used = 0
    first = True

    for so in list(sos):
        used += so.size
        # allow most recent version to be stored even if it is itself over
        # limit
        if used > limit and not first:
            so.delete()
        first = False
