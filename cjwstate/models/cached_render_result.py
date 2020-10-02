from dataclasses import dataclass
from typing import Any, Dict, List
from cjwkernel.types import RenderError, TableMetadata


@dataclass
class CachedRenderResult:
    """
    Result of a module render() call.

    This is stored in the database as `step.cached_render_result_*`,
    and you select it by selecting `step.cached_render_result`.
    (This is unconventional. Many DB designers would leap to use OneToOneField;
    but that has no pros, only cons.)

    Part of this result is also stored on disk. The bucket is always
    minio.CachedRenderResultsBucket, and the key is always
    "wf-{workflow.id}/wfm-{step.id}/delta-{delta.id}.dat".

    The `cjwstate.rendercache` module manipulates this data.
    """

    workflow_id: int
    step_id: int
    delta_id: int
    status: str  # "ok", "error", "unreachable"
    errors: List[RenderError]
    json: Dict[str, Any]
    table_metadata: TableMetadata
