from pathlib import Path
from typing import Optional
import uuid
from django.conf import settings
import pandas as pd
from pandas.util import hash_pandas_object
import pyarrow
import pyarrow.parquet
from cjwstate import minio, parquet
from cjwstate.models import StoredObject, WfModule, Workflow


BUCKET = minio.StoredObjectsBucket


def hash_table(table: pd.DataFrame) -> str:
    """Build a hash useful in comparing data frames for equality."""
    h = hash_pandas_object(table).sum()  # xor would be nice, but whatevs
    h = h if h > 0 else -h  # stay positive (sum often overflows)
    return str(h)


def parquet_file_to_pandas(path: Path) -> pd.DataFrame:
    if path.stat().st_size == 0:
        return pd.DataFrame()
    else:
        arrow_table = pyarrow.parquet.read_table(str(path), use_threads=False)
        return arrow_table.to_pandas(
            date_as_object=False, deduplicate_objects=True, ignore_metadata=True
        )  # TODO ensure dictionaries stay dictionaries


def _build_key(workflow_id: int, wf_module_id: int) -> str:
    """Build a helpful S3 key."""
    return f"{workflow_id}/{wf_module_id}/{uuid.uuid1()}.dat"


def _read_dataframe_from_minio(bucket: str, key: str) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from Parquet file stored on minio.

    Return None if:

    * there is no file on minio
    * the file on minio cannot be read

    TODO return a pyarrow.Table instead.
    """
    try:
        return parquet.read(bucket, key)
    except (FileNotFoundError, parquet.FastparquetCouldNotHandleFile):
        return None


def read_dataframe_from_stored_object(
    stored_object: StoredObject
) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from StoredObject.

    Return None if:

    * there is no file on minio
    * the file on minio cannot be read

    TODO return a pyarrow.Table instead.
    """
    if stored_object.bucket == "":  # ages ago, "empty" meant bucket='', key=''
        return pd.DataFrame()
    return _read_dataframe_from_minio(stored_object.bucket, stored_object.key)


def read_fetched_dataframe_from_wf_module(
    wf_module: WfModule
) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from wf_module's user-selected StoredObject.

    Return None if:

    * there is no user-selected StoredObject
    * the user-selected StoredObject does not exist (the selection isn't a foreign key)
    * there is no file on minio
    * the file on minio cannot be read

    TODO return a pyarrow.Table instead.
    """
    try:
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
    except StoredObject.DoesNotExist:
        return None
    return read_dataframe_from_stored_object(stored_object)


def create_stored_object(
    workflow: Workflow, wf_module: WfModule, table: pd.DataFrame, hash: str
) -> StoredObject:
    """
    Write and return a new StoredObject.

    The caller should call enforce_storage_limits() after calling this.
    """
    key = _build_key(workflow.id, wf_module.id)
    size = parquet.write_pandas(minio.StoredObjectsBucket, key, table)
    stored_object = wf_module.stored_objects.create(
        bucket=BUCKET, key=key, size=size, hash=hash
    )
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

    for so in sos:
        used += so.size
        if used > limit and not first:
            # allow most recent version to be stored even if it is itself over
            # limit
            so.delete()
        first = False
