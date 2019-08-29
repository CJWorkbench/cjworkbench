import json
from typing import List, Optional
import pandas as pd
import pyarrow
from cjwkernel.pandas.types import ProcessResult
from cjwstate import parquet
from server.models import WfModule, Workflow, CachedRenderResult
from server import minio


BUCKET = minio.CachedRenderResultsBucket


WF_MODULE_FIELDS = [
    "cached_render_result_delta_id",
    "cached_render_result_error",
    "cached_render_result_json",
    "cached_render_result_quick_fixes",
    "cached_render_result_columns",
    "cached_render_result_status",
    "cached_render_result_nrows",
]


class CorruptCacheError(Exception):
    """
    Data in the database does not match data in minio.
    """


def parquet_prefix(workflow_id: int, wf_module_id: int) -> str:
    """
    "Directory" name in the `minio.CachedRenderResultsBucket` bucket.

    The name ends with '/'. _All_ cached data for the specified WfModule is
    stored under that prefix.
    """
    return "wf-%d/wfm-%d/" % (workflow_id, wf_module_id)


def parquet_key(workflow_id: int, wf_module_id: int, delta_id: int) -> str:
    """
    Path to a file, where the specified result should be saved.
    """
    return "%sdelta-%d.dat" % (parquet_prefix(workflow_id, wf_module_id), delta_id)


def crr_parquet_key(crr: CachedRenderResult) -> str:
    return parquet_key(crr.workflow_id, crr.wf_module_id, crr.delta_id)


def cache_render_result(
    workflow: Workflow, wf_module: WfModule, delta_id: int, result: ProcessResult
) -> CachedRenderResult:
    """
    Save the given ProcessResult for later viewing.

    Raise AssertionError if `delta_id` is not what we expect.

    Since this alters data, be sure to call it within a lock:

        with workflow.cooperative_lock():
            wf_module.refresh_from_db()  # may change delta_id
            wf_module.cache_render_result(delta_id, result)
    """
    assert delta_id == wf_module.last_relevant_delta_id
    assert result is not None

    json_bytes = json.dumps(result.json).encode("utf-8")
    quick_fixes = result.quick_fixes

    wf_module.cached_render_result_delta_id = delta_id
    wf_module.cached_render_result_error = result.error
    wf_module.cached_render_result_status = result.status
    wf_module.cached_render_result_json = json_bytes
    wf_module.cached_render_result_quick_fixes = [qf.to_dict() for qf in quick_fixes]
    wf_module.cached_render_result_columns = result.columns
    wf_module.cached_render_result_nrows = len(result.dataframe)

    # Now we get to the part where things can end up inconsistent. Try to
    # err on the side of not-caching when that happens.
    delete_parquet_files_for_wf_module(
        workflow.id, wf_module.id
    )  # makes old cache inconsistent
    wf_module.save(update_fields=WF_MODULE_FIELDS)  # makes new cache inconsistent
    parquet.write(
        BUCKET, parquet_key(workflow.id, wf_module.id, delta_id), result.dataframe
    )  # makes new cache consistent


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
    """
    Hydrate a CachedRenderResult into a ProcessResult, by reading from disk.

    If the CachedRenderResult is invalid, raise CorruptCacheError.

    TODO switch retval to cjwkernel.types.RenderResultOk
    """
    dataframe = _parquet_read_dataframe(
        minio.CachedRenderResultsBucket, crr_parquet_key(crr)
    )
    if not len(dataframe.columns) and len(crr.columns):
        # We cached data, and now the file is gone. That's a ValueError.
        raise CorruptCacheError
    return ProcessResult(
        dataframe,
        error=crr.error,
        json=crr.json,
        quick_fixes=crr.quick_fixes,
        columns=crr.columns,
    )


def read_cached_render_result_as_arrow(
    crr: CachedRenderResult, *, only_columns: Optional[List[str]] = None
) -> pyarrow.Table:
    """
    Read a cached Parquet file into an mmapped Arrow table.

    If the CachedRenderResult is invalid, raise CorruptCacheError.

    If the CachedRenderResult is an "error" result, return an empty table.
    """
    try:
        return parquet.read_arrow_table(
            BUCKET, crr_parquet_key(crr), only_columns=only_columns
        )
    except FileNotFoundError:
        raise CorruptCacheError


def delete_parquet_files_for_wf_module(workflow_id: int, wf_module_id: int) -> None:
    """
    Delete all Parquet files cached for `wf_module`.

    Different deltas on the same module produce different Parquet
    filenames. This function removes all of them.

    This deletes from minio but not from the database. Beware -- this can leave
    the database in an inconsistent state.
    """
    minio.remove_recursive(BUCKET, parquet_prefix(workflow_id, wf_module_id))


def clear_cached_render_result_for_wf_module(wf_module: WfModule) -> None:
    """
    Delete a CachedRenderResult, if it exists.

    This deletes the Parquet file from disk, _then_ empties relevant
    database fields and saves them (and only them).
    """
    delete_parquet_files_for_wf_module(wf_module.workflow_id, wf_module.id)

    wf_module.cached_render_result_delta_id = None
    wf_module.cached_render_result_error = ""
    wf_module.cached_render_result_json = b"null"
    wf_module.cached_render_result_quick_fixes = []
    wf_module.cached_render_result_status = None
    wf_module.cached_render_result_columns = None
    wf_module.cached_render_result_nrows = None

    wf_module.save(update_fields=WF_MODULE_FIELDS)
