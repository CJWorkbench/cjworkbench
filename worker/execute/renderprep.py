from functools import partial, singledispatch
from typing import Any, Dict, List, Optional
import pandas as pd
from server.models import Params, Tab
from server.models.param_field import ParamDType
from server.types import Column, StepResultShape
from .types import TabCycleError, TabOutputUnreachableError, UnneededExecution


class TabOutput:
    def __init__(self, slug: str, name: str, columns: List[Column],
                 dataframe: pd.DataFrame):
        self.slug = slug
        self.name = name
        self.columns = columns
        self.dataframe = dataframe


class RenderContext:
    def __init__(
        self,
        workflow_id: int,
        input_table_shape: StepResultShape,
        tab_shapes: Dict[str, Optional[StepResultShape]]
    ):
        self.workflow_id = workflow_id
        self.input_table_shape = input_table_shape
        self.tab_shapes = tab_shapes


def get_param_values(
    params: Params,
    context: RenderContext,
) -> Dict[str, Any]:
    """
    Convert `params` to a dict we'll pass to a module `render()` function.

    Concretely:

        * `Tab` parameters become Optional[TabOutput] (declared here)
        * Eliminate missing `Tab`s: they'll be `None`
        * Raise `TabCycleError` if a chosen Tab has not been rendered
        * `column` parameters become '' if they aren't input columns
        * `multicolumn` parameters lose values that aren't input columns

    This uses database connections, and it's slow! (It needs to load input tab
    data.) Be sure the Workflow is locked while you call it.
    """
    return {
        **clean_value(params.schema, params.values, context),
        **params.secrets
    }


# singledispatch primer: `clean_value(dtype, value, context)` will choose its
# logic based on the _type_ of `dtype`. (Handily, it'll prefer a specific class
# to its parent class.)
#
# TODO abstract this pattern. The recursion parts seem like they should be
# written in just one place.
@singledispatch
def clean_value(dtype: ParamDType, value: Any,
                context: RenderContext) -> Any:
    """
    Ensure `value` fits the Params dict `render()` expects.

    The most basic implementation is to just return `value`: it looks a lot
    like the dict we pass `render()`. But we have special-case implementations
    for a few dtypes.
    """
    return value  # fallback method


@clean_value.register(ParamDType.Tab)
def _(dtype: ParamDType.Tab, value: str, context: RenderContext) -> TabOutput:
    tab_slug = value
    try:
        shape = context.tab_shapes[tab_slug]
    except KeyError:
        # It's a tab that doesn't exist.
        return None
    if shape is None:
        # It's an un-rendered tab. Or at least, the executor _tells_ us it's
        # un-rendered. That means there's a tab-cycle.
        raise TabCycleError
    if shape.status != 'ok':
        raise TabOutputUnreachableError

    # Load Tab output from database. Assumes we've locked the workflow.
    try:
        tab = Tab.objects.get(
            workflow_id=context.workflow_id,
            is_deleted=False,
            slug=tab_slug
        )
    except Tab.DoesNotExist:
        # If the Tab doesn't exist, someone deleted it mid-render. (We already
        # verified that the tab has been rendered -- that was
        # context.tab_shapes[tab_slug].) So our param is stale.
        raise UnneededExecution

    wf_module = tab.live_wf_modules.last()
    if wf_module is None:
        # empty tab -> empty output
        raise TabOutputUnreachableError

    crr = wf_module.cached_render_result
    if crr is None:
        # ... but tab_shapes implies we just cached the correct result! It
        # looks like that version must be stale.
        raise UnneededExecution

    result = crr.result  # read Parquet file from disk (slow)
    return TabOutput(tab_slug, tab.name, result.columns, result.dataframe)


@clean_value.register(ParamDType.Column)
def _(dtype: ParamDType.Column, value: str, context: RenderContext) -> str:
    input_colnames = set(c.name for c in context.input_table_shape.columns)
    return dtype.omit_missing_table_columns(value, input_colnames)


@clean_value.register(ParamDType.Multicolumn)
def _(
    dtype: ParamDType.Multicolumn,
    value: str,
    context: RenderContext
) -> str:
    input_colnames = set(c.name for c in context.input_table_shape.columns)
    return dtype.omit_missing_table_columns(value, input_colnames)


# ... and then the methods for recursing
@clean_value.register(ParamDType.List)
def _(
    dtype: ParamDType.List,
    value: List[Any],
    context: RenderContext
) -> List[Any]:
    inner_dtype = dtype.inner_dtype
    inner_clean = partial(clean_value, inner_dtype)
    return [inner_clean(v, context) for v in value]


@clean_value.register(ParamDType.Dict)
def _(
    dtype: ParamDType.Dict,
    value: Dict[str, Any],
    context: RenderContext
) -> Dict[str, Any]:
    return dict(
        (k, clean_value(dtype.properties[k], v, context))
        for k, v in value.items()
    )


@clean_value.register(ParamDType.Map)
def _(
    dtype: ParamDType.Map,
    value: Dict[str, Any],
    context: RenderContext
) -> Dict[str, Any]:
    value_dtype = dtype.value_dtype
    value_clean = partial(clean_value, value_dtype)
    return dict(
        (k, value_clean(v, context))
        for k, v in value.items()
    )
