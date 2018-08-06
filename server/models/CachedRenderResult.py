import os
import json
from typing import Optional
from django.core.files.storage import default_storage
from server.modules.types import ProcessResult
from server import parquet


def _parquet_path(workflow_id: int, wf_module_id: int):
    """Return the path on disk where we save Parquet. for this wf_module."""
    path = f'cached-render-results/wf-{workflow_id}/wfm-{wf_module_id}.dat'
    return default_storage.path(path)


class CachedRenderResult:
    """
    Result of a ModuleImpl.render() call.

    This is stored in the database as `wf_module.cached_render_result_*`,
    and you select it by selecting `wf_module.get_cached_render_result()`.
    (This is unconventional. The convention is to use OneToOneField, but that
    has no pros, only cons.
    """

    def __init__(self, workflow_id: int, wf_module_id: int,
                 workflow_revision: int, result: ProcessResult):
        self.workflow_id = workflow_id
        self.wf_module_id = wf_module_id
        self.workflow_revision = workflow_revision
        self.result = result

    @property
    def parquet_path(self):
        return _parquet_path(self.workflow_id, self.wf_module_id)

    @staticmethod
    def from_wf_module(wf_module: 'WfModule') -> 'CachedRenderResult':
        """Reads the CachedRenderResult or None from a WfModule (and disk)."""
        if wf_module.cached_render_result_workflow_revision is None:
            return None

        workflow_revision = wf_module.cached_render_result_workflow_revision
        workflow_id = wf_module.workflow_id
        wf_module_id = wf_module.id

        parquet_path = _parquet_path(workflow_id, wf_module_id)
        try:
            dataframe = parquet.read(parquet_path)
        except OSError:
            # Two possibilities:
            #
            # 1. The file is missing.
            # 2. The file is empty (we write empty files in assign_wf_module)
            dataframe = None

        error = wf_module.cached_render_result_error
        # cached_render_result_json is sometimes a memoryview
        json_bytes = bytes(wf_module.cached_render_result_json)
        if json_bytes:
            json_dict = json.loads(json_bytes)
        else:
            json_dict = None

        result = ProcessResult(dataframe=dataframe, error=error,
                               json=json_dict)
        return CachedRenderResult(workflow_id=workflow_id,
                                  wf_module_id=wf_module_id,
                                  workflow_revision=workflow_revision,
                                  result=result)

    @staticmethod
    def _clear_wf_module(wf_module: 'WfModule') -> None:
        workflow_id = wf_module.cached_render_result_workflow_id

        wf_module.cached_render_result_workflow_id = None
        wf_module.cached_render_result_workflow_revision = None
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
                         workflow_revision: Optional[int],
                         result: Optional[ProcessResult]
                         ) -> Optional['CachedRenderResult']:
        """
        Write `result` to `wf_module`'s fields.

        If either argument is None, clear the fields.
        """
        if workflow_revision is None or result is None:
            return CachedRenderResult._clear_wf_module(wf_module)

        if wf_module.workflow_id is None:
            raise ValueError('Cannot cache render result on orphan WfModule')

        ret = CachedRenderResult(workflow_id=wf_module.workflow_id,
                                 wf_module_id=wf_module.id,
                                 workflow_revision=workflow_revision,
                                 result=result)

        error = result.error
        json_bytes = json.dumps(result.json).encode('utf-8')
        revision = workflow_revision

        wf_module.cached_render_result_workflow_id = wf_module.workflow_id
        wf_module.cached_render_result_workflow_revision = revision
        wf_module.cached_render_result_workflow_error = error
        wf_module.cached_render_result_json = json_bytes

        os.makedirs(os.path.dirname(ret.parquet_path), exist_ok=True)

        if result is None:
            try:
                os.remove(ret.parquet_path)
            except FileNotFoundError:
                pass
        elif result.dataframe.empty:
            # Can't write an empty dataframe as parquet, so instead we'll write
            # an empty file. We need to write _something_to handle this case:
            #
            # 1. Cache a non-empty table
            # 2. Cache an empty table (we are here)
            #
            # ... if this write were a no-op, then a read would return the
            # value from 1.
            with open(ret.parquet_path, 'wb') as f:
                f.write(b'')
        else:
            parquet.write(ret.parquet_path, result.dataframe)

        return ret
