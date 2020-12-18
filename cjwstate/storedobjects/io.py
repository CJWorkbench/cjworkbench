import uuid
from pathlib import Path
from typing import ContextManager, Optional

from django.conf import settings
from django.utils import timezone

from cjwkernel.util import tempfile_context
from cjwstate import minio
from cjwstate.models import Step, StoredObject
from cjwstate.util import find_deletable_ids

BUCKET = minio.StoredObjectsBucket


def downloaded_file(stored_object: StoredObject, dir=None) -> ContextManager[Path]:
    """Context manager to download and yield `path`, the StoredObject's file.

    Raise FileNotFoundError if the object is missing.

    Usage:

        try:
            with storedobjects.downloaded_file(stored_object) as path:
                # do something with `path`, a `pathlib.Path`
        except FileNotFoundError:
            # file does not exist....
    """
    if stored_object.size == 0:
        # Some stored objects with size=0 do not have key. These are valid:
        # they represent empty files.
        return tempfile_context(prefix="storedobjects-empty-file", dir=dir)
    else:
        # raises FileNotFoundError
        return minio.temporarily_download(
            minio.StoredObjectsBucket, stored_object.key, dir=dir
        )


def _build_key(workflow_id: int, step_id: int) -> str:
    """Build a helpful S3 key."""
    return f"{workflow_id}/{step_id}/{uuid.uuid1()}.dat"


def create_stored_object(
    workflow_id: int,
    step_id: int,
    path: Path,
    stored_at: Optional[timezone.datetime] = None,
) -> StoredObject:
    """Write and return a new StoredObject.

    The caller should call enforce_storage_limits() after calling this.

    Raise IntegrityError if a database race prevents saving this. Raise a minio
    error if writing to minio failed. In case of partial completion, a
    StoredObject will exist in the database but no file will be saved in minio.
    """
    if stored_at is None:
        stored_at = timezone.now()
    key = _build_key(workflow_id, step_id)
    size = path.stat().st_size
    stored_object = StoredObject.objects.create(
        stored_at=stored_at,
        step_id=step_id,
        key=key,
        size=size,
        hash="unhashed",
    )
    minio.fput_file(BUCKET, key, path)
    return stored_object


def delete_old_files_to_enforce_storage_limits(*, step: Step) -> None:
    """Delete old fetches that bring us past MAX_BYTES_FETCHES_PER_STEP or
    MAX_N_FETCHES_PER_STEP.

    We can't let every workflow grow forever.
    """
    to_delete = find_deletable_ids(
        ids_and_sizes=step.stored_objects.order_by("-stored_at").values_list(
            "id", "size"
        ),
        n_limit=settings.MAX_N_FETCHES_PER_STEP,
        size_limit=settings.MAX_BYTES_FETCHES_PER_STEP,
    )

    if to_delete:
        # QuerySet.delete() sends pre_delete signal, which deletes from S3
        # ref: https://docs.djangoproject.com/en/2.2/ref/models/querysets/#django.db.models.query.QuerySet.delete
        step.stored_objects.filter(id__in=to_delete).delete()
