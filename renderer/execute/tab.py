from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, FrozenSet
from cjworkbench.sync import database_sync_to_async
from cjwkernel.pandas.types import ProcessResult, StepResultShape
from cjwstate.rendercache import open_cached_render_result
from cjwstate.models import WfModule, Workflow, Tab
from cjwstate.models.param_spec import ParamDType
from .wf_module import execute_wfmodule, locked_wf_module


logger = logging.getLogger(__name__)


class cached_property:
    """
    Memoizes a property by replacing the function with the retval.
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self._func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self

        func = self._func
        value = func(obj)
        obj.__dict__[func.__name__] = value
        return value


@dataclass(frozen=True)
class ExecuteStep:
    wf_module: WfModule
    schema: ParamDType.Dict
    params: Dict[str, Any]


@dataclass(frozen=True)
class TabFlow:
    """
    Sequence of steps in a single Tab.

    This is a data class: there are no database queries here. In particular,
    querying for `.stale_steps` gives the steps that were stale _at the time of
    construction_.
    """

    tab: Tab
    steps: List[ExecuteStep]

    @property
    def tab_slug(self) -> str:
        return self.tab.slug

    @property
    def tab_name(self) -> str:
        return self.tab.name

    @cached_property
    def first_stale_index(self) -> int:
        """
        Index into `self.steps` of the first WfModule that needs rendering.

        `None` if the entire flow is fresh.
        """
        cached_results = [step.wf_module.cached_render_result for step in self.steps]
        try:
            # Stale WfModule means its .cached_render_result is None.
            return cached_results.index(None)
        except ValueError:
            return None

    @cached_property
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

    @cached_property
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
        return self.steps[fresh_index].wf_module

    @cached_property
    def input_tab_slugs(self) -> FrozenSet[str]:
        """
        Slugs of tabs that are used as _input_ into this tab's steps.
        """
        ret = set()
        for step in self.steps:
            schema = step.schema
            slugs = set(schema.find_leaf_values_with_dtype(ParamDType.Tab, step.params))
            ret.update(slugs)
        return frozenset(ret)


@database_sync_to_async
def _load_input_from_cache(workflow: Workflow, flow: TabFlow) -> ProcessResult:
    last_fresh_wfm = flow.last_fresh_wf_module
    if last_fresh_wfm is None:
        return ProcessResult()
    else:
        # raises UnneededExecution
        with locked_wf_module(workflow, last_fresh_wfm) as safe_wfm:
            crr = safe_wfm.cached_render_result
            assert crr is not None  # otherwise it's not fresh, see?

            # Read the entire input Parquet file.
            with open_cached_render_result(crr) as arrow_result:
                return ProcessResult.from_arrow(arrow_result)


async def execute_tab_flow(
    workflow: Workflow, flow: TabFlow, tab_shapes: Dict[str, Optional[StepResultShape]]
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
    logger.debug(
        "Rendering Tab(%d, %s - %s)", workflow.id, flow.tab_slug, flow.tab.name
    )

    # Execute one module at a time.
    #
    # We don't hold any lock throughout the loop: the loop can take a long
    # time; it might be run multiple times simultaneously (even on
    # different computers); and `await` doesn't work with locks.
    last_result = await _load_input_from_cache(workflow, flow)
    for step in flow.stale_steps:
        last_result = await execute_wfmodule(
            workflow,
            step.wf_module,
            step.params,
            flow.tab_name,
            last_result,
            tab_shapes,
        )
    return last_result
