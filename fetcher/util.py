from typing import Optional
import pandas as pd
from cjwstate.rendercache import read_cached_render_result, CorruptCacheError
from server import parquet
from server.models import CachedRenderResult, StoredObject, WfModule


def _read_dataframe_from_minio(bucket: str, key: str) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from Parquet file stored on minio.

    Return None if:

    * there is no file on minio
    * the file on minio cannot be read
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
    """
    try:
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
    except StoredObject.DoesNotExist:
        return None
    return read_dataframe_from_stored_object(stored_object)


def read_dataframe_from_cached_render_result(
    crr: CachedRenderResult
) -> Optional[pd.DataFrame]:
    """
    Read DataFrame from a CachedRenderREsult.

    Return None if:

        * there is no file on minio
        * the file on minio cannot be read
    """
    try:
        result = read_cached_render_result(crr)
    except CorruptCacheError:
        return None
    return result.dataframe
