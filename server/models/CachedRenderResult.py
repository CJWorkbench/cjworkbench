import json
from typing import Any, Dict, List, Optional
import pandas as pd
from cjworkbench.types import ProcessResult, QuickFix, TableShape
from server import minio, parquet


WfModuleFields = [
    "cached_render_result_delta_id",
    "cached_render_result_error",
    "cached_render_result_json",
    "cached_render_result_quick_fixes",
    "cached_render_result_columns",
    "cached_render_result_status",
    "cached_render_result_nrows",
]


def parquet_prefix(workflow_id: int, wf_module_id: int) -> str:
    """
    "Directory" name in the `minio.CachedRenderResultsBucket` bucket.

    The name ends with '/'. _All_ cached data for the specified WfModule is
    stored under that prefix.
    """
    return "wf-%d/wfm-%d/" % (workflow_id, wf_module_id)


class CachedRenderResult:
    """
    Result of a module render() call.

    This is stored in the database as `wf_module.cached_render_result_*`,
    and you select it by selecting `wf_module.get_cached_render_result()`.
    (This is unconventional. The convention is to use OneToOneField, but that
    has no pros, only cons.)

    Part of this result is also stored on disk. Read it with read_dataframe().

    Use this heuristic to decide when to use CachedRenderResult:

        * CachedRenderResult is cheap: low RAM, low CPU, low I/O.
        * CachedRenderResult.result and .read_dataframe() are expensive.
    """

    def __init__(
        self,
        workflow_id: int,
        wf_module_id: int,
        delta_id: int,
        status: str,
        error: str,
        json: Optional[Dict[str, Any]],
        quick_fixes: List[QuickFix],
        table_shape: TableShape,
    ):
        self.workflow_id = workflow_id
        self.wf_module_id = wf_module_id
        self.delta_id = delta_id
        self.status = status
        self.error = error
        self.json = json
        self.quick_fixes = quick_fixes
        self.table_shape = table_shape

    @property
    def columns(self):
        return self.table_shape.columns

    @property
    def nrows(self):
        return self.table_shape.nrows

    @property
    def parquet_key(self):
        """
        Path to a file, used by the `parquet` module.
        """
        return "%sdelta-%d.dat" % (
            parquet_prefix(self.workflow_id, self.wf_module_id),
            self.delta_id,
        )

    def read_dataframe(self, *args, **kwargs):
        """
        Read Parquet file as a dataframe (costing network requests).

        Pass *args and **kwargs to `fastparquet.ParquetFile.to_pandas()`.

        TODO make this raise OSError/FastparquetCouldNotHandleFile. (Currently
        we return an empty dataframe on error.)
        """
        try:
            return parquet.read(
                minio.CachedRenderResultsBucket, self.parquet_key, args, kwargs
            )
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

    @property
    def result(self):
        """
        Convert to ProcessResult -- which means reading the parquet file.

        It's best to avoid this operation when possible.

        TODO make this _not_ a @property -- since it's so expensive (it makes a
        big network request).
        """
        if not hasattr(self, "_result"):
            dataframe = self.read_dataframe()
            self._result = ProcessResult(
                dataframe,
                self.error,
                json=self.json,
                quick_fixes=self.quick_fixes,
                columns=self.columns,
            )

        return self._result

    def __bool__(self):
        return True

    def __len__(self):
        """
        Scan on-disk header for number of rows.

        This does not read the entire DataFrame.

        TODO make all callers read `.nrows` instead.
        """
        return self.nrows

    @staticmethod
    def from_wf_module(wf_module: "WfModule") -> "CachedRenderResult":
        """
        Read the CachedRenderResult or None from a WfModule.

        This does not read the _result_ from disk. If you want a "snapshot in
        time" of the ProcessResult you need a lock, like this:

            # Lock the workflow, making sure we don't overwrite data
            with workflow.cooperative_lock():
                # Read from database
                cached_result = wf_module.get_cached_render_result()
                # Read from disk
                cached_result.result

        (There's not much point in reading from disk within this method,
        because a "snapshot in time" is impossible anyway: half the data is in
        the database and the other half is on disk.)
        """
        if wf_module.cached_render_result_delta_id is None:
            return None

        delta_id = wf_module.cached_render_result_delta_id
        status = wf_module.cached_render_result_status
        error = wf_module.cached_render_result_error
        columns = wf_module.cached_render_result_columns
        nrows = wf_module.cached_render_result_nrows

        # TODO [2019-01-24] once we've deployed and wiped all caches, nix this
        # 'columns' check and assume 'columns' is always set when we get here
        if columns is None:
            # this cached value is stale because _Workbench_ has been updated
            # and doesn't support it any more
            return None

        # cached_render_result_json is sometimes a memoryview
        json_bytes = bytes(wf_module.cached_render_result_json)
        if json_bytes:
            json_dict = json.loads(json_bytes)
        else:
            json_dict = None

        quick_fixes = wf_module.cached_render_result_quick_fixes
        if not quick_fixes:
            quick_fixes = []
        # Coerce from dict to QuickFixes
        quick_fixes = [QuickFix(**qf) for qf in quick_fixes]

        ret = CachedRenderResult(
            workflow_id=wf_module.workflow_id,
            wf_module_id=wf_module.id,
            delta_id=delta_id,
            status=status,
            error=error,
            json=json_dict,
            quick_fixes=quick_fixes,
            table_shape=TableShape(nrows, columns),
        )
        # Keep in mind: ret.result has not been loaded yet. It might not exist
        # when we do try reading it.
        return ret

    @staticmethod
    def delete_parquet_files_for_wf_module(wf_module: "WfModule") -> None:
        """
        Ensures there are no Parquet files cached for `wf_module`.

        Different deltas on the same module produce different Parquet
        filenames. This function removes all of them.

        This leaves `wf_module.cached_render_result` invalid: it will continue
        to exist in the database, but callers who try to read from it will
        see `FileNotFoundError.
        """
        minio.remove_recursive(
            minio.CachedRenderResultsBucket,
            parquet_prefix(wf_module.workflow_id, wf_module.id),
        )

    @staticmethod
    def clear_wf_module(wf_module: "WfModule") -> None:
        """
        Delete our CachedRenderResult, if it exists.

        This deletes the Parquet file from disk, _then_ empties relevant
        database fields and saves them (and only them).
        """
        CachedRenderResult.delete_parquet_files_for_wf_module(wf_module)

        wf_module.cached_render_result_delta_id = None
        wf_module.cached_render_result_error = ""
        wf_module.cached_render_result_json = b"null"
        wf_module.cached_render_result_quick_fixes = []
        wf_module.cached_render_result_status = None
        wf_module.cached_render_result_columns = None
        wf_module.cached_render_result_nrows = None

        wf_module.save(update_fields=WfModuleFields)

    @staticmethod
    def assign_wf_module(
        wf_module: "WfModule", delta_id: int, result: ProcessResult
    ) -> "CachedRenderResult":
        """
        Write `result` to `wf_module`'s fields and to disk.
        """
        assert delta_id == wf_module.last_relevant_delta_id
        assert result is not None

        json_bytes = json.dumps(result.json).encode("utf-8")
        quick_fixes = result.quick_fixes

        wf_module.cached_render_result_delta_id = delta_id
        wf_module.cached_render_result_error = result.error
        wf_module.cached_render_result_status = result.status
        wf_module.cached_render_result_json = json_bytes
        wf_module.cached_render_result_quick_fixes = [
            qf.to_dict() for qf in quick_fixes
        ]
        wf_module.cached_render_result_columns = result.columns
        wf_module.cached_render_result_nrows = len(result.dataframe)

        CachedRenderResult.delete_parquet_files_for_wf_module(wf_module)

        ret = CachedRenderResult.from_wf_module(wf_module)
        ret._result = result  # no need to read from disk
        parquet.write(
            minio.CachedRenderResultsBucket, ret.parquet_key, result.dataframe
        )

        wf_module.save(update_fields=WfModuleFields)

        return ret
