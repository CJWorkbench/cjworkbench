import contextlib
from pathlib import Path
from typing import ContextManager
import cjwparquet
import pyarrow
from cjwkernel.types import ArrowTable, RenderResult, TableMetadata
from cjwkernel.util import json_encode, tempfile_context
from cjwstate import s3
from cjwstate.models import Step, Workflow, CachedRenderResult


BUCKET = s3.CachedRenderResultsBucket


STEP_FIELDS = [
    "cached_render_result_delta_id",
    "cached_render_result_errors",
    "cached_render_result_json",
    "cached_render_result_columns",
    "cached_render_result_status",
    "cached_render_result_nrows",
]


class CorruptCacheError(Exception):
    """Data in the database does not match data in s3."""


def parquet_prefix(workflow_id: int, step_id: int) -> str:
    """'Directory' name in the `s3.CachedRenderResultsBucket` bucket.

    The name ends with '/'. _All_ cached data for the specified Step is
    stored under that prefix.
    """
    return "wf-%d/wfm-%d/" % (workflow_id, step_id)


def parquet_key(workflow_id: int, step_id: int, delta_id: int) -> str:
    """
    Path to a file, where the specified result should be saved.
    """
    return "%sdelta-%d.dat" % (parquet_prefix(workflow_id, step_id), delta_id)


def crr_parquet_key(crr: CachedRenderResult) -> str:
    return parquet_key(crr.workflow_id, crr.step_id, crr.delta_id)


def cache_render_result(
    workflow: Workflow, step: Step, delta_id: int, result: RenderResult
) -> None:
    """Save `result` for later viewing.

    Raise AssertionError if `delta_id` is not what we expect.

    Since this alters data, be sure to call it within a lock:

        with workflow.cooperative_lock():
            step.refresh_from_db()  # may change delta_id
            cache_render_result(workflow, step, delta_id, result)
    """
    assert delta_id == step.last_relevant_delta_id
    assert result is not None

    json_bytes = json_encode(result.json).encode("utf-8")
    if not result.table.metadata.columns:
        if result.errors:
            status = "error"
        else:
            status = "unreachable"
    else:
        status = "ok"

    step.cached_render_result_delta_id = delta_id
    step.cached_render_result_errors = result.errors
    step.cached_render_result_status = status
    step.cached_render_result_json = json_bytes
    step.cached_render_result_columns = result.table.metadata.columns
    step.cached_render_result_nrows = result.table.metadata.n_rows

    # Now we get to the part where things can end up inconsistent. Try to
    # err on the side of not-caching when that happens.
    delete_parquet_files_for_step(workflow.id, step.id)  # makes old cache inconsistent
    step.save(update_fields=STEP_FIELDS)  # makes new cache inconsistent
    if result.table.metadata.columns:  # only write non-zero-column tables
        with tempfile_context() as parquet_path:
            cjwparquet.write(parquet_path, result.table.table)
            s3.fput_file(
                BUCKET, parquet_key(workflow.id, step.id, delta_id), parquet_path
            )  # makes new cache consistent


@contextlib.contextmanager
def downloaded_parquet_file(crr: CachedRenderResult, dir=None) -> ContextManager[Path]:
    """Context manager to download and yield `path`, a hopefully-Parquet file.

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
                s3.temporarily_download(BUCKET, crr_parquet_key(crr), dir=dir)
            )
        except FileNotFoundError:
            raise CorruptCacheError

        yield path


def load_cached_render_result(crr: CachedRenderResult, path: Path) -> RenderResult:
    """Return a RenderResult equivalent to the one passed to `cache_render_result()`.

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
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        return RenderResult(
            ArrowTable.from_zero_column_metadata(
                TableMetadata(crr.table_metadata.n_rows, [])
            ),
            crr.errors,
            crr.json,
        )

    # raises CorruptCacheError
    with downloaded_parquet_file(crr) as parquet_path:
        try:
            # raises ArrowIOError
            cjwparquet.convert_parquet_file_to_arrow_file(parquet_path, path)
        except pyarrow.ArrowIOError as err:
            raise CorruptCacheError from err
    # TODO handle validation errors => CorruptCacheError
    arrow_table = ArrowTable.from_trusted_file(path, crr.table_metadata)
    return RenderResult(arrow_table, crr.errors, crr.json)


@contextlib.contextmanager
def open_cached_render_result(crr: CachedRenderResult) -> ContextManager[RenderResult]:
    """Yield a RenderResult equivalent to the one passed to `cache_render_result()`.

    Raise CorruptCacheError if the cached data does not match `crr`. That can
    mean:

        * The cached Parquet file is corrupt
        * The cached Parquet file is missing
        * `crr` is stale -- the cached result is for a different delta. This
          could be detected by a `Workflow.cooperative_lock()`, too, should the
          caller want to distinguish this error from the others.

    The returned RenderResult is backed by an mmapped file on disk, so it
    doesn't require much physical RAM.
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        yield RenderResult(
            ArrowTable.from_zero_column_metadata(
                TableMetadata(crr.table_metadata.n_rows, [])
            ),
            crr.errors,
            crr.json,
        )
        return

    with tempfile_context(prefix="cached-render-result") as arrow_path:
        # raise CorruptCacheError (deleting `arrow_path` in the process)
        result = load_cached_render_result(crr, arrow_path)

        yield result


def read_cached_render_result_slice_as_text(
    crr: CachedRenderResult, format: str, only_columns: range, only_rows: range
) -> str:
    """Call `parquet-to-text-stream` and return its output.

    Ignore out-of-range rows and columns.

    Raise CorruptCacheError if the cached data does not match `crr`. That can
    mean:

        * The cached Parquet file is corrupt
        * The cached Parquet file is missing
        * `crr` is stale -- the cached result is for a different delta. This
          could be detected by a `Workflow.cooperative_lock()`, too, should the
          caller want to distinguish this error from the others.

    To limit the amount of text stored in RAM, use relatively small ranges for
    `only_columns` and `only_rows`.

    This uses `parquet-to-text-stream` with `--row-range` and `--column-range`.
    Read `parquet-to-text-stream` documentation to see how nulls and floats are
    handled in your chosen format (`csv` or `json`). (In a nutshell: it's
    mostly non-lossy, though CSV can't represent `null`.)
    """
    if not crr.table_metadata.columns:
        # Zero-column tables aren't written to cache
        return {}

    try:
        with downloaded_parquet_file(crr) as parquet_path:
            return cjwparquet.read_slice_as_text(
                parquet_path,
                format=format,
                only_columns=only_columns,
                only_rows=only_rows,
            )
    except (pyarrow.ArrowIOError, FileNotFoundError):  # FIXME unit-test
        raise CorruptCacheError


def delete_parquet_files_for_step(workflow_id: int, step_id: int) -> None:
    """Delete all Parquet files cached for `step`.

    Different deltas on the same module produce different Parquet
    filenames. This function removes all of them.

    This deletes from s3 but not from the database. Beware -- this can leave
    the database in an inconsistent state.
    """
    s3.remove_recursive(BUCKET, parquet_prefix(workflow_id, step_id))


def clear_cached_render_result_for_step(step: Step) -> None:
    """Delete a CachedRenderResult, if it exists.

    This deletes the Parquet file from disk, _then_ empties relevant
    database fields and saves them (and only them).
    """
    delete_parquet_files_for_step(step.workflow_id, step.id)

    step.cached_render_result_delta_id = None
    step.cached_render_result_errors = []
    step.cached_render_result_json = b"null"
    step.cached_render_result_status = None
    step.cached_render_result_columns = None
    step.cached_render_result_nrows = None

    step.save(update_fields=STEP_FIELDS)
