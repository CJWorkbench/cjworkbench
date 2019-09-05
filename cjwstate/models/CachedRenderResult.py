from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from cjwkernel.pandas.types import TableShape
from cjwkernel.types import RenderError


@dataclass
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

    workflow_id: int
    wf_module_id: int
    delta_id: int
    status: str  # "ok", "error", "unreachable"
    errors: List[RenderError]
    json: Optional[Dict[str, Any]]
    table_shape: TableShape

    @property
    def columns(self):
        return self.table_shape.columns

    @property
    def nrows(self):
        return self.table_shape.nrows

    def __bool__(self):
        # overridden so `len(self) == 0` is still `bool(self) is True`
        return True

    def __len__(self):
        """
        Number of rows.

        This does not read the DataFrame.

        TODO make all callers read `.nrows` instead.
        """
        return self.nrows
