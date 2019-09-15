import contextlib
import os
from pathlib import Path
import tempfile
from typing import ContextManager
import uuid
from django.conf import settings
from cjwstate import minio
from cjwstate.models import StoredObject, WfModule


BUCKET = minio.StoredObjectsBucket


@contextlib.contextmanager
def _empty_temporary_file() -> ContextManager[Path]:
    fd, filename = tempfile.mkstemp(prefix="storedobjects-empty-file")
    try:
        os.close(fd)
        yield Path(filename)
    finally:
        os.unlink(filename)


def downloaded_file(stored_object: StoredObject) -> ContextManager[Path]:
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
        return _empty_temporary_file()
    else:
        # raises FileNotFoundError
        return minio.temporarily_download(stored_object.bucket, stored_object.key)


def _build_key(workflow_id: int, wf_module_id: int) -> str:
    """Build a helpful S3 key."""
    return f"{workflow_id}/{wf_module_id}/{uuid.uuid1()}.dat"


def create_stored_object(
    workflow_id: int, wf_module_id: int, path: Path, hash: str
) -> StoredObject:
    """
    Write and return a new StoredObject.

    The caller should call enforce_storage_limits() after calling this.

    Raise IntegrityError if a database race prevents saving this. Raise a minio
    error if writing to minio failed. In case of partial completion, a
    StoredObject will exist in the database but no file will be saved in minio.
    """
    key = _build_key(workflow_id, wf_module_id)
    size = path.stat().st_size
    stored_object = StoredObject.objects.create(
        wf_module_id=wf_module_id, bucket=BUCKET, key=key, size=size, hash=hash
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
