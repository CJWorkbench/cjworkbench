from functools import lru_cache
import logging
from typing import Dict, List, Optional, Set, Tuple
from channels.db import database_sync_to_async
from cjworkbench.types import ProcessResult, StepResultShape
from server.models import Params, WfModule, Workflow, Tab
from server.models.param_spec import ParamDType
from .wf_module import execute_wfmodule, locked_wf_module


_memoize = lru_cache(maxsize=1)
logger = logging.getLogger(__name__)


ExecuteStep = Tuple[WfModule, Params]


# @dataclass in python 3.7
class TabFlow:
    """
    Sequence of steps in a single Tab.

    This is a data class: there are no database queries here. In particular,
    querying for `.stale_steps` gives the steps that were stale _at the time of
    construction_.
    """
    def __init__(self, tab: Tab, steps: List[ExecuteStep]):
        self.tab = tab
        self.steps = steps

    @property
    def tab_slug(self) -> str:
        return self.tab.slug

    @property
    def tab_name(self) -> str:
        return self.tab.name

    @property
    @_memoize
    def first_stale_index(self) -> int:
        """
        Index into `self.steps` of the first WfModule that needs rendering.

        `None` if the entire flow is fresh.
        """
        cached_results = [step[0].cached_render_result for step in self.steps]
        try:
            # Stale WfModule means its .cached_render_result is None.
            return cached_results.index(None)
        except ValueError:
            return None

    @property
    @_memoize
    def stale_steps(self) -> List[ExecuteStep]:
        """
        Just the steps of `self.steps` that need rendering.

        `[]` if the entire flow is fresh.
        """
        index = self.first_stale_index
        if index is None:
            return []
        else:
            return self.steps[index:]

    @property
    @_memoize
    def last_fresh_wf_module(self) -> Optional[WfModule]:
        """
        The first fresh step.
        """
        stale_index = self.first_stale_index
        if stale_index is None:
            stale_index = len(self.steps)
        fresh_index = stale_index - 1
        if fresh_index < 0:
            return None
        wf_module, params = self.steps[fresh_index]
        return wf_module

    @property
    @_memoize
    def input_tab_slugs(self) -> Set[str]:
        """
        Slugs of tabs that are used as _input_ into this tab's steps.
        """
        ret = set()
        for wf_module, params in self.steps:
            schema = params.schema
            slugs = set(schema.find_leaf_values_with_dtype(ParamDType.Tab,
                                                           params.values))
            ret.update(slugs)
        return ret


@database_sync_to_async
def _load_input_from_cache(workflow: Workflow,
                           flow: TabFlow) -> ProcessResult:
    last_fresh_wfm = flow.last_fresh_wf_module
    if last_fresh_wfm is None:
        return ProcessResult()
    else:
        # raises UnneededExecution
        with locked_wf_module(workflow, last_fresh_wfm) as safe_wfm:
            crr = safe_wfm.cached_render_result
            assert crr is not None  # otherwise it's not fresh, see?

            # Read the entire input Parquet file.
            return crr.result


async def execute_tab_flow(
    workflow: Workflow,
    flow: TabFlow,
    tab_shapes: Dict[str, Optional[StepResultShape]]
) -> ProcessResult:
    """
    Ensure `flow.tab.live_wf_modules` all cache fresh render results.

    `tab_shapes.keys()` must be ordered as the Workflow's tabs are.

    Raise `UnneededExecution` if something changes underneath us such that we
    can't guarantee all render results will be fresh. (The remaining execution
    is "unneeded" because we assume another render has been queued.)

    WEBSOCKET NOTES: each wf_module is executed in turn. After each execution,
    we notify clients of its new columns and status.
    """
    logger.debug('Rendering Tab(%d, %s - %s)', workflow.id, flow.tab_slug,
                 flow.tab.name)

    # Execute one module at a time.
    #
    # We don't hold any lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on
    # different computers); and `await` doesn't work with locks.
    last_result = await _load_input_from_cache(workflow, flow)
    for wf_module, params in flow.stale_steps:
        last_result = await execute_wfmodule(workflow, wf_module, params,
                                             flow.tab_name, last_result,
                                             tab_shapes)
    return last_result
