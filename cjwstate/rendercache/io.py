import contextlib
from pathlib import Path
from typing import Any, ContextManager, Dict, List, Optional
import pyarrow
from cjwkernel.types import ArrowTable, RenderResult, TableMetadata
from cjwkernel.util import json_encode, tempfile_context
from cjwstate import minio, parquet
from cjwstate.models import WfModule, Workflow, CachedRenderResult


BUCKET = minio.CachedRenderResultsBucket


WF_MODULE_FIELDS = [
    "cached_render_result_delta_id",
    "cached_render_result_errors",
    "cached_render_result_error",  # DELETEME
    "cached_render_result_quick_fixes",  # DELETEME
    "cached_render_result_json",
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
    workflow: Workflow, wf_module: WfModule, delta_id: int, result: RenderResult
) -> None:
    """
    Save `result` for later viewing.

    Raise AssertionError if `delta_id` is not what we expect.

    Since this alters data, be sure to call it within a lock:

        with workflow.cooperative_lock():
            wf_module.refresh_from_db()  # may change delta_id
            cache_render_result(workflow, wf_module, delta_id, result)
    """
    assert delta_id == wf_module.last_relevant_delta_id
    assert result is not None

    json_bytes = json_encode(result.json).encode("utf-8")
    if not result.table.metadata.columns:
        if result.errors:
            status = "error"
        else:
            status = "unreachable"
    else:
        status = "ok"

    wf_module.cached_render_result_delta_id = delta_id
    wf_module.cached_render_result_errors = result.errors
    wf_module.cached_render_result_error = ""  # DELETEME
    wf_module.cached_render_result_quick_fixes = []  # DELETEME
    wf_module.cached_render_result_status = status
    wf_module.cached_render_result_json = json_bytes
    wf_module.cached_render_result_columns = result.table.metadata.columns
    wf_module.cached_render_result_nrows = result.table.metadata.n_rows

    # Now we get to the part where things can end up inconsistent. Try to
    # err on the side of not-caching when that happens.
    delete_parquet_files_for_wf_module(
        workflow.id, wf_module.id
    )  # makes old cache inconsistent
    wf_module.save(update_fields=WF_MODULE_FIELDS)  # makes new cache inconsistent
    if result.table.metadata.columns:  # only write non-zero-column tables
        with tempfile_context() as parquet_path:
            parquet.write(parquet_path, result.table.table)
            minio.fput_file(
                BUCKET, parquet_key(workflow.id, wf_module.id, delta_id), parquet_path
            )  # makes new cache consistent


@contextlib.contextmanager
def downloaded_parquet_file(crr: CachedRenderResult, dir=None) -> ContextManager[Path]:
    """
    Context manager to download and yield `path`, a hopefully-Parquet file.

    This is cheaper than open_cached_render_result() because it does not parse
    the file. Use this function when you suspect you won't need the table data.

    Raise CorruptCacheError if the cached data is missing.

    Usage:

        try:
            with rendercache.downloaded_parquet_file(crr) as path:
                # do something with `path`, a `pathlib.Path`
        except rendercache.CorruptCacheError:
            # file does not exist....
    """
    with contextlib.ExitStack() as ctx:
        try:
            path = ctx.enter_context(
                minio.temporarily_download(BUCKET, crr_parquet_key(crr), dir=dir)
            )
        except FileNotFoundError:
            raise CorruptCacheError

        yield path


def load_cached_render_result(
    crr: CachedRenderResult, path: Path, only_columns: Optional[List[str]] = None
) -> RenderResult:
    """
    Return a RenderResult equivalent to the one passed to `cache_render_result()`.

    Raise CorruptCacheError if the cached data does not match `crr`. That can
    mean:

        * The cached Parquet file is corrupt
        * The cached Parquet file is missing
        * `crr` is stale -- the cached result is for a different delta. This
          could be detected by a `Workflow.cooperative_lock()`, too, should the
          caller want to distinguish this error from the others.

    The returned RenderResult is backed by an mmapped file on disk -- the one
    supplied as `path`. It doesn't require much physical RAM: the Linux kernel
    may page out data we aren't using.

    If only_columns is a list of column names, the yielded RenderResult only
    contains the specified columns.
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        return RenderResult(
            ArrowTable(None, TableMetadata(crr.table_metadata.n_rows, [])),
            crr.errors,
            crr.json,
        )

    try:
        with downloaded_parquet_file(crr) as parquet_path:
            parquet.convert_parquet_file_to_arrow_file(
                parquet_path, path, only_columns=only_columns
            )
    except FileNotFoundError:
        raise CorruptCacheError  # FIXME add unit test
    # TODO handle validation errors => CorruptCacheError
    if only_columns is None:
        table_metadata = crr.table_metadata
    else:
        table_metadata = TableMetadata(
            crr.table_metadata.n_rows,
            [c for c in crr.table_metadata.columns if c.name in only_columns],
        )
    arrow_table = ArrowTable(path, table_metadata)
    return RenderResult(arrow_table, crr.errors, crr.json)


@contextlib.contextmanager
def open_cached_render_result(
    crr: CachedRenderResult, only_columns: Optional[List[str]] = None
) -> ContextManager[RenderResult]:
    """
    Yield a RenderResult equivalent to the one passed to `cache_render_result()`.

    Raise CorruptCacheError if the cached data does not match `crr`. That can
    mean:

        * The cached Parquet file is corrupt
        * The cached Parquet file is missing
        * `crr` is stale -- the cached result is for a different delta. This
          could be detected by a `Workflow.cooperative_lock()`, too, should the
          caller want to distinguish this error from the others.

    The returned RenderResult is backed by an mmapped file on disk, so it
    doesn't require much physical RAM.

    If only_columns is a list of column names, the yielded RenderResult only
    contains the specified columns.
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        yield RenderResult(
            ArrowTable(None, TableMetadata(crr.table_metadata.n_rows, [])),
            crr.errors,
            crr.json,
        )
        return

    with tempfile_context(prefix="cached-render-result") as arrow_path:
        # raise CorruptCacheError (deleting `arrow_path` in the process)
        result = load_cached_render_result(crr, arrow_path, only_columns=only_columns)

        yield result


def read_cached_render_result_pydict(
    crr: CachedRenderResult, only_columns: List[str], only_rows: range
) -> Dict[str, List[Any]]:
    """
    Return a dict mapping column name to data (Python objects).

    Python data consumes RAM, so you must specify columns and rows.

    `retval.keys()` is in table-column order (not `only_columns` order).

    Missing rows and columns are ignored.

    `NaN` is returned as float("nan").

    Raise CorruptCacheError if the cached data does not match `crr`. That can
    mean:

        * The cached Parquet file is corrupt
        * The cached Parquet file is missing
        * `crr` is stale -- the cached result is for a different delta. This
          could be detected by a `Workflow.cooperative_lock()`, too, should the
          caller want to distinguish this error from the others.
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        return {}

    try:
        with downloaded_parquet_file(crr) as parquet_path:
            return parquet.read_pydict(parquet_path, only_columns, only_rows)
    except (pyarrow.ArrowIOError, FileNotFoundError):  # FIXME unit-test
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
    wf_module.cached_render_result_errors = []
    wf_module.cached_render_result_error = ""
    wf_module.cached_render_result_json = b"null"
    wf_module.cached_render_result_quick_fixes = []
    wf_module.cached_render_result_status = None
    wf_module.cached_render_result_columns = None
    wf_module.cached_render_result_nrows = None

    wf_module.save(update_fields=WF_MODULE_FIELDS)
