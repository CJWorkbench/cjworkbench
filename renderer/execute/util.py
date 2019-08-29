import pandas as pd
from cjwkernel.pandas.types import ProcessResult
from server import minio, parquet
from server.models import CachedRenderResult


def _parquet_read_dataframe(bucket: str, key: str) -> pd.DataFrame:
    try:
        return parquet.read(bucket, key)
    except OSError:
        # Two possibilities:
        #
        # 1. The file is missing.
        # 2. The file is empty. (We used to write empty files in
        #    assign_wf_module.)
        #
        # Either way, our cached DataFrame is "empty", and we represent
        # that as None.
        return pd.DataFrame()
    except parquet.FastparquetCouldNotHandleFile:
        # Treat bugs as "empty file"
        return pd.DataFrame()


def read_cached_render_result(crr: CachedRenderResult) -> ProcessResult:
    dataframe = _parquet_read_dataframe(
        minio.CachedRenderResultsBucket, crr.parquet_key
    )
    return ProcessResult(
        dataframe,
        error=crr.error,
        json=crr.json,
        quick_fixes=crr.quick_fixes,
        columns=crr.columns,
    )
