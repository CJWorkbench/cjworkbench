from typing import Any, Dict, List, Optional
from cjwkernel.pandas.types import QuickFix, TableShape


class CachedRenderResult:
    """
    Result of a module render() call.

    This is stored in the database as `wf_module.cached_render_result_*`,
    and you select it by selecting `wf_module.cached_render_result`.
    (This is unconventional. Many DB designers would leap to use OneToOneField;
    but that has no pros, only cons.)

    Part of this result is also stored on disk. The bucket is always
    minio.CachedRenderResultsBucket, and the key is always
    "wf-{workflow.id}/wfm-{wf_module.id}/delta-{delta.id}.dat".

    The `cjwstate.rendercache` module manipulates this data.
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

    def __bool__(self):
        return True

    def __len__(self):
        """
        Scan on-disk header for number of rows.

        This does not read the entire DataFrame.

        TODO make all callers read `.nrows` instead.
        """
        return self.nrows
