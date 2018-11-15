import os
import json
from typing import Any, Dict, List, Optional
from django.core.files.storage import default_storage
import pandas
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from server.modules.types import Column, ProcessResult, QuickFix
from server import parquet


def _parquet_path(workflow_id: int, wf_module_id: int):
    """Return the path on disk where we save Parquet. for this wf_module."""
    path = f'cached-render-results/wf-{workflow_id}/wfm-{wf_module_id}.dat'
    return default_storage.path(path)


def _dtype_to_column_type(dtype) -> str:
    """Determine if a pandas dtype is 'text', 'number' or 'datetime'."""
    if is_numeric_dtype(dtype):
        return 'number'
    elif is_datetime64_dtype(dtype):
        return 'datetime'
    elif dtype == object or dtype == 'category':
        return 'text'
    else:
        raise ValueError(f'Unknown column type: {dtype}')


class CachedRenderResult:
    """
    Result of a ModuleImpl.render() call.

    This is stored in the database as `wf_module.cached_render_result_*`,
    and you select it by selecting `wf_module.get_cached_render_result()`.
    (This is unconventional. The convention is to use OneToOneField, but that
    has no pros, only cons.)

    Part of this result is also stored on disk. Read it as `parquet_file`.
    """

    def __init__(self, workflow_id: int, wf_module_id: int, delta_id: int,
                 status: str, error: str, json: Optional[Dict[str, Any]],
                 quick_fixes: List[QuickFix]):
        self.workflow_id = workflow_id
        self.wf_module_id = wf_module_id
        self.delta_id = delta_id
        self.status = status
        self.error = error
        self.json = json
        self.quick_fixes = quick_fixes

    @property
    def parquet_path(self):
        return _parquet_path(self.workflow_id, self.wf_module_id)

    @property
    def parquet_file(self):
        if not hasattr(self, '_parquet_file'):
            try:
                self._parquet_file = parquet.read_header(self.parquet_path)
            except OSError:
                # Two possibilities:
                #
                # 1. The file is missing.
                # 2. The file is empty. (We used to write empty files in
                #    assign_wf_module.)
                #
                # Either way, our cached DataFrame is "empty", and we represent
                # that as None.
                self._parquet_file = None
            except parquet.FastparquetCouldNotHandleFile:
                # Treat bugs as "empty file"
                self._parquet_file = None

        # TODO keep a handle on the file, to guarantee it doesn't disappear
        # from disk until after this CachedRenderResult is destroyed. Until
        # then, every read from self._parquet_file is a race.
        return self._parquet_file

    @property
    def result(self):
        """
        Convert to ProcessResult -- which means reading the parquet file.

        It's best to avoid this operation when possible.
        """
        if not hasattr(self, '_result'):
            if self.status == 'ok' and self.parquet_file:
                # At this point, we know the file exists. (It may be an empty
                # DataFrame.)
                dataframe = self.parquet_file.to_pandas()
            else:
                dataframe = pandas.DataFrame()

            self._result = ProcessResult(dataframe, self.error,
                                         json=self.json,
                                         quick_fixes=self.quick_fixes)

        return self._result

    @property
    def column_names(self) -> List[str]:
        """
        Scan on-disk header for column names.

        This does not read the entire DataFrame.
        """
        if hasattr(self, '_result'):
            return self._result.column_names
        elif self.parquet_file:
            return self.parquet_file.columns
        else:
            return []

    def __bool__(self):
        return True

    def __len__(self):
        """
        Scan on-disk header for number of rows.

        This does not read the entire DataFrame.
        """
        if hasattr(self, '_result'):
            return len(self._result.dataframe)
        elif self.parquet_file:
            return self.parquet_file.count
        else:
            return 0

    @property
    def column_types(self) -> List[str]:
        """
        Scan on-disk header for column types -- text, number or datetime.

        This does not read the entire DataFrame.
        """
        if hasattr(self, '_result'):
            return self._result.column_types
        elif self.parquet_file:
            dtypes = self.parquet_file.dtypes.values()
        else:
            dtypes = []

        return [_dtype_to_column_type(t) for t in dtypes]

    @property
    def columns(self):
        """Scan on-disk header for columns and their types."""
        return [Column(n, t)
                for n, t in zip(self.column_names, self.column_types)]

    @staticmethod
    def from_wf_module(wf_module: 'WfModule') -> 'CachedRenderResult':
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
        workflow_id = wf_module.workflow_id
        wf_module_id = wf_module.id

        status = wf_module.cached_render_result_status
        error = wf_module.cached_render_result_error

        # cached_render_result_json is sometimes a memoryview
        json_bytes = bytes(wf_module.cached_render_result_json)
        if json_bytes:
            json_dict = json.loads(json_bytes)
        else:
            json_dict = None

        quick_fixes = wf_module.cached_render_result_quick_fixes
        if not quick_fixes:
            quick_fixes = []
        # Coerce from tuples to QuickFixes
        quick_fixes = [QuickFix.coerce(qf) for qf in quick_fixes]

        ret = CachedRenderResult(workflow_id=workflow_id,
                                 wf_module_id=wf_module_id, delta_id=delta_id,
                                 status=status, error=error, json=json_dict,
                                 quick_fixes=quick_fixes)
        # Keep in mind: ret.parquet_file has not been loaded yet. That means
        # this result is _not_ a snapshot in time, and you must be careful not
        # to treat it as such.
        return ret

    @staticmethod
    def _clear_wf_module(wf_module: 'WfModule') -> None:
        workflow_id = wf_module.cached_render_result_workflow_id

        wf_module.cached_render_result_workflow_id = None
        wf_module.cached_render_result_delta_id = None
        wf_module.cached_render_result_error = ''
        wf_module.cached_render_result_json = b'null'
        wf_module.cached_render_result_quick_fixes = []

        if workflow_id is not None:
            # We're setting non-None to None. That means there's probably
            # a file to delete.
            parquet_path = _parquet_path(workflow_id, wf_module.id)
            try:
                os.remove(parquet_path)
            except FileNotFoundError:
                pass

    @staticmethod
    def assign_wf_module(wf_module: 'WfModule',
                         delta_id: Optional[int],
                         result: Optional[ProcessResult]
                         ) -> Optional['CachedRenderResult']:
        """
        Write `result` to `wf_module`'s fields and to disk.

        If either argument is None, clear the fields.
        """
        if delta_id is None or result is None:
            return CachedRenderResult._clear_wf_module(wf_module)

        if wf_module.workflow_id is None:
            raise ValueError('Cannot cache render result on orphan WfModule')

        if result:
            error = result.error
            status = result.status
            json_dict = result.json
            json_bytes = json.dumps(result.json).encode('utf-8')
            quick_fixes = result.quick_fixes
        else:
            error = ''
            status = None
            json_dict = None
            json_bytes = ''
            quick_fixes = []

        wf_module.cached_render_result_workflow_id = wf_module.workflow_id
        wf_module.cached_render_result_delta_id = delta_id
        wf_module.cached_render_result_error = error
        wf_module.cached_render_result_status = status
        wf_module.cached_render_result_json = json_bytes
        wf_module.cached_render_result_quick_fixes = [qf.to_dict()
                                                      for qf in quick_fixes]

        parquet_path = _parquet_path(wf_module.workflow_id, wf_module.id)

        os.makedirs(os.path.dirname(parquet_path), exist_ok=True)

        if result is None:
            try:
                os.remove(parquet_path)
            except FileNotFoundError:
                pass
            return None
        else:
            parquet.write(parquet_path, result.dataframe)

            ret = CachedRenderResult(workflow_id=wf_module.workflow_id,
                                     wf_module_id=wf_module.id,
                                     delta_id=delta_id, status=status,
                                     error=error, json=json_dict,
                                     quick_fixes=quick_fixes)
            ret._result = result  # no need to read from disk
            return ret
