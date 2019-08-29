from typing import Optional
import pandas as pd
from server import parquet
from server.models import StoredObject, WfModule


def read_dataframe_from_stored_object(
    stored_object: StoredObject
) -> Optional[pd.DataFrame]:
    try:
        if stored_object.size == 0:  # ages-old objects with bucket='', key=''
            return pd.DataFrame()
        return parquet.read(stored_object.bucket, stored_object.key)
    except (FileNotFoundError, parquet.FastparquetCouldNotHandleFile):
        return None


def read_fetched_dataframe_from_wf_module(wf_module: WfModule) -> pd.DataFrame:
    try:
        stored_object = wf_module.stored_objects.get(
            stored_at=wf_module.stored_data_version
        )
    except StoredObject.DoesNotExist:
        return None
    return read_dataframe_from_stored_object(stored_object)
