import os
import json
from typing import Any, Dict, List, Optional
from django.core.files.storage import default_storage
import pandas
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from server.modules.types import Column, ProcessResult
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

    def __init__(self, workflow_id: int, wf_module_id: int,
                 delta_id: int, error: str, json: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.wf_module_id = wf_module_id
        self.delta_id = delta_id
        self.error = error
        self.json = json

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
            except IndexError:
                # TODO nix this when fastparquet resolves
                # https://github.com/dask/fastparquet/issues/361
                #
                # The file has a zero-length column list, and fastparquet can't
                # handle that.
                #
                # Our cached DataFrame should be "empty". No columns means no
                # rows.
                self._parquet_file = None

        return self._parquet_file

    @property
    def result(self):
        if not hasattr(self, '_result'):
            if self.parquet_file:
                # At this point, we know the file exists. (It may be an empty
                # DataFrame.)
                dataframe = self.parquet_file.to_pandas()
            else:
                dataframe = pandas.DataFrame()

            self._result = ProcessResult(dataframe, self.error, self.json)

        return self._result

    @property
    def column_names(self) -> List[str]:
        """
        Scan on-disk header for column names.

        This does not read the entire DataFrame.
        """
        if self.parquet_file:
            return self.parquet_file.columns
        else:
            return []

    @property
    def column_types(self) -> List[str]:
        """
        Scan on-disk header for column types -- text, number or datetime.

        This does not read the entire DataFrame.
        """
        if self.parquet_file:
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

        error = wf_module.cached_render_result_error
        # cached_render_result_json is sometimes a memoryview
        json_bytes = bytes(wf_module.cached_render_result_json)
        if json_bytes:
            json_dict = json.loads(json_bytes)
        else:
            json_dict = None

        ret = CachedRenderResult(workflow_id=workflow_id,
                                 wf_module_id=wf_module_id, delta_id=delta_id,
                                 error=error, json=json_dict)
        # Keep in mind: ret.parquet_file has not been loaded yet. That means
        # this result is _not_ a snapshot in time, and you must be careful not
        # to treat it as such.
        return ret

    @staticmethod
    def _clear_wf_module(wf_module: 'WfModule') -> None:
        workflow_id = wf_module.cached_render_result_workflow_id

        wf_module.cached_render_result_workflow_id = None
        wf_module.cached_render_result_delta_id = None
        wf_module.cached_render_result_json = b'null'
        wf_module.cached_render_result_error = ''

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
            json_dict = result.json
            json_bytes = json.dumps(result.json).encode('utf-8')
        else:
            error = ''
            json_dict = None
            json_bytes = ''

        wf_module.cached_render_result_workflow_id = wf_module.workflow_id
        wf_module.cached_render_result_delta_id = delta_id
        wf_module.cached_render_result_error = error
        wf_module.cached_render_result_json = json_bytes

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

            return CachedRenderResult(workflow_id=wf_module.workflow_id,
                                      wf_module_id=wf_module.id,
                                      delta_id=delta_id,
                                      error=error, json=json_dict)
