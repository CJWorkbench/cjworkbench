from typing import Any, Dict, List

import pyarrow as pa

from cjwmodule.types import RenderError

from cjwkernel.tests.util import arrow_table_context
from cjwkernel.types import LoadedRenderResult
from cjwkernel.validate import read_columns
from cjwstate.models.step import Step
from cjwstate.models.workflow import Workflow
from .io import cache_render_result


def write_to_rendercache(
    workflow: Workflow,
    step: Step,
    delta_id: int,
    table: pa.Table,
    errors: List[RenderError] = [],
    json: Dict[str, Any] = {},
) -> None:
    with arrow_table_context(table) as (path, table):
        result = LoadedRenderResult(
            path=path,
            table=table,
            columns=read_columns(table, full=False),
            errors=errors,
            json=json,
        )

        # use the caller-provided delta ID: no assertion
        old_last_relevant_delta_id = step.last_relevant_delta_id
        step.last_relevant_delta_id = delta_id
        try:
            cache_render_result(workflow, step, delta_id, result)
        finally:
            step.last_relevant_delta_id = old_last_relevant_delta_id
