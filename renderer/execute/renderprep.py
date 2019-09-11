from dataclasses import dataclass
from functools import partial, singledispatch
import os
import re
import pathlib
import tempfile
import weakref
from typing import Any, Dict, List, Optional, Union
from cjwkernel.types import ArrowTable, Params, RenderResult, Tab, TabOutput
from cjwstate import minio
from cjwstate.models import UploadedFile
from cjwstate.models.param_spec import ParamDType
from .types import TabCycleError, TabOutputUnreachableError, PromptingError


FilesystemUnsafeChars = re.compile("[^-_.,()a-zA-Z0-9]")


class PromptErrorAggregator:
    def __init__(self):
        self.groups = {}  # found_type => { wanted_types => column_names }
        # Errors are first-come-first-reported, per type. We get that because
        # Python 3.7+ dicts iterate in insertion order.

    def extend(self, errors: List[PromptingError.WrongColumnType]) -> None:
        for error in errors:
            self.add(error)

    def add(self, error: PromptingError.WrongColumnType) -> None:
        if "text" in error.wanted_types:
            found_type = None
        else:
            found_type = error.found_type
        group = self.groups.setdefault(found_type, {})
        names = group.setdefault(error.wanted_types, [])
        for name in error.column_names:
            if name not in names:
                names.append(name)

    def raise_if_nonempty(self):
        if not self.groups:
            return

        errors = []
        for found_type, group in self.groups.items():
            for wanted_types, column_names in group.items():
                errors.append(
                    PromptingError.WrongColumnType(
                        column_names, found_type, wanted_types
                    )
                )
        raise PromptingError(errors)


@dataclass(frozen=True)
class _TabData:
    tab: Tab
    result: Optional[RenderResult]

    @property
    def slug(self) -> str:
        return self.tab.slug


class RenderContext:
    def __init__(
        self,
        wf_module_id: int,
        input_table: ArrowTable,
        # assume tab_results keys are ordered the way the user ordered the tabs.
        tab_results: Dict[Tab, Optional[RenderResult]],
        # params is a HACK to let column selectors rely on a tab_parameter,
        # which is a _root-level_ parameter. So when we're walking the tree of
        # params, we need to keep a handle on the root ...  which is ugly and
        # [2019-02-07, adamhooper] I'm on a deadline today to publish join
        # okthxbye.
        #
        # This is especially ugly because RenderContext only exists for
        # get_param_values(), and get_param_values() also takes `params`. Ugh.
        params: Dict[str, Any],
    ):
        self.wf_module_id = wf_module_id
        self.input_table = input_table
        self.tabs: Dict[str, _TabData] = {
            k.slug: _TabData(k, v) for k, v in tab_results.items()
        }
        self.params = params

    def output_columns_for_tab_parameter(self, tab_parameter):
        if tab_parameter is None:
            # Common case: param selects from the input table
            return {c.name: c for c in self.input_table.metadata.columns}

        # Rare case: there's a "tab" parameter, and the column selector is
        # selecting from _that_ tab's output columns.

        # valid schema means no KeyError
        tab_slug = self.params[tab_parameter]

        try:
            tab_data = self.tabs[tab_slug]
        except KeyError:
            # Tab does not exist
            return {}
        if tab_data.result is None or tab_data.result.status != "ok":
            # Tab has a cycle or other error.
            return {}

        return {c.name: c for c in tab_data.result.table.metadata.columns}


def get_param_values(
    schema: ParamDType.Dict, params: Dict[str, Any], context: RenderContext
) -> Params:
    """
    Convert `params` to a dict we'll pass to a module `render()` function.

    Concretely:

        * `Tab` parameters become Optional[TabOutput] (declared here)
        * Eliminate missing `Tab`s: they'll be `None`
        * Raise `TabCycleError` if a chosen Tab has not been rendered
        * `column` parameters become '' if they aren't input columns
        * `multicolumn` parameters lose values that aren't input columns
        * Raise `PromptingError` if a chosen column is of the wrong type
          (so the caller can render a ProcessResult with errors and quickfixes)

    This uses database connections, and it's slow! (It needs to load input tab
    data.) Be sure the Workflow is locked while you call it.
    """
    values: Dict[str, Any] = clean_value(schema, params, context)
    return Params(values)


# singledispatch primer: `clean_value(dtype, value, context)` will choose its
# logic based on the _type_ of `dtype`. (Handily, it'll prefer a specific class
# to its parent class.)
#
# The recursive logic in fetchprep.py was copy/pasted from renderprep.py.
#
# TODO abstract this pattern. The recursion parts seem like they should be
# written in just one place.
@singledispatch
def clean_value(dtype: ParamDType, value: Any, context: RenderContext) -> Any:
    """
    Ensure `value` fits the Params dict `render()` expects.

    The most basic implementation is to just return `value`: it looks a lot
    like the dict we pass `render()`. But we have special-case implementations
    for a few dtypes.

    Raise TabCycleError, TabOutputUnreachableError or UnneededExecution if
    render cannot be called and there's nothing we can do to fix that.
    
    Raise PromptingError if we want to ask the user to fix stuff instead of
    calling render(). (Recursive implementations must concatenate these.)
    """
    return value  # fallback method


@clean_value.register(ParamDType.Float)
def _(
    dtype: ParamDType.Float, value: Union[int, float], context: RenderContext
) -> float:
    # ParamDType.Float can have `int` values (because values come from
    # json.parse(), which only gives Numbers so can give "3" instead of
    # "3.0". We want to pass that as `float` in the `params` dict.
    return float(value)


class WeakreffablePath(pathlib.PosixPath):
    """Exactly like pathlib.Path, but weakref.finalize works on it."""


@clean_value.register(ParamDType.File)
def _(
    dtype: ParamDType.File, value: Optional[str], context: RenderContext
) -> Optional[pathlib.Path]:
    """
    Convert a `file` String-encoded UUID to a tempfile `pathlib.Path`.

    The return value:

    * Points to a temporary file containing all bytes
    * Has the same suffix as the originally-uploaded file
    * Will have its file deleted when it goes out of scope
    """
    if value is None:
        return None
    try:
        uploaded_file = UploadedFile.objects.get(
            uuid=value, wf_module_id=context.wf_module_id
        )
    except UploadedFile.DoesNotExist:
        return None

    # UploadedFile.name may not be POSIX-compliant. We want the filename to
    # have the same suffix as the original: that helps with filetype
    # detection. We also put the UUID in the name so debug messages help
    # devs find the original file.
    name = FilesystemUnsafeChars.sub("-", uploaded_file.name)
    suffix = "".join(pathlib.PurePath(name).suffixes)
    fd, filename = tempfile.mkstemp(suffix=suffix, prefix=value)
    os.close(fd)  # we just want the empty file; no need to have it open
    # Build our retval: it'll delete the file when it's destroyed
    path = WeakreffablePath(filename)
    weakref.finalize(path, os.unlink, filename)
    try:
        # Overwrite the file
        minio.download(uploaded_file.bucket, uploaded_file.key, path)
    except FileNotFoundError:
        # tempfile will be deleted by weakref
        return None
    return path


@clean_value.register(ParamDType.Tab)
def _(dtype: ParamDType.Tab, value: str, context: RenderContext) -> TabOutput:
    tab_slug = value
    try:
        tab_data = context.tabs[tab_slug]
    except KeyError:
        # It's a tab that doesn't exist.
        return None
    tab_result = tab_data.result
    if tab_result is None:
        # It's an un-rendered tab. Or at least, the executor _tells_ us it's
        # un-rendered. That means there's a tab-cycle.
        raise TabCycleError
    if tab_result.status != "ok":
        raise TabOutputUnreachableError

    return TabOutput(tab_data.tab, tab_result.table)


@clean_value.register(ParamDType.Column)
def _(dtype: ParamDType.Column, value: str, context: RenderContext) -> str:
    valid_columns = context.output_columns_for_tab_parameter(dtype.tab_parameter)
    if value not in valid_columns:
        return ""  # Null column

    column = valid_columns[value]
    if dtype.column_types and column.type.name not in dtype.column_types:
        if "text" in dtype.column_types:
            found_type = None
        else:
            found_type = column.type.name
        raise PromptingError(
            [PromptingError.WrongColumnType([value], found_type, dtype.column_types)]
        )

    return value


@clean_value.register(ParamDType.Multicolumn)
def _(dtype: ParamDType.Multicolumn, value: List[str], context: RenderContext) -> str:
    valid_columns = context.output_columns_for_tab_parameter(dtype.tab_parameter)

    error_agg = PromptErrorAggregator()
    requested_colnames = set(value)

    valid_colnames = []
    # ignore colnames not in valid_columns
    # iterate in table order
    for colname, column in valid_columns.items():
        if colname not in requested_colnames:
            continue

        if dtype.column_types and column.type.name not in dtype.column_types:
            if "text" in dtype.column_types:
                found_type = None
            else:
                found_type = column.type.name
            error_agg.add(
                PromptingError.WrongColumnType(
                    [column.name], found_type, dtype.column_types
                )
            )
        else:
            valid_colnames.append(column.name)

    error_agg.raise_if_nonempty()

    return valid_colnames


@clean_value.register(ParamDType.Multichartseries)
def _(
    dtype: ParamDType.Multichartseries,
    value: List[Dict[str, str]],
    context: RenderContext,
) -> List[Dict[str, str]]:
    # Recurse to clean_value(ParamDType.Column) to clear missing columns
    inner_clean = partial(clean_value, dtype.inner_dtype)

    ret = []
    error_agg = PromptErrorAggregator()

    for v in value:
        try:
            clean_v = inner_clean(v, context)
            if clean_v["column"]:  # it's a valid column
                ret.append(clean_v)
        except PromptingError as err:
            error_agg.extend(err.errors)

    error_agg.raise_if_nonempty()
    return ret


# ... and then the methods for recursing
@clean_value.register(ParamDType.List)
def clean_value_list(
    dtype: ParamDType.List, value: List[Any], context: RenderContext
) -> List[Any]:
    inner_clean = partial(clean_value, dtype.inner_dtype)
    ret = []
    error_agg = PromptErrorAggregator()
    for v in value:
        try:
            ret.append(inner_clean(v, context))
        except PromptingError as err:
            error_agg.extend(err.errors)
    error_agg.raise_if_nonempty()
    return ret


@clean_value.register(ParamDType.Multitab)
def _(
    dtype: ParamDType.Multitab, value: List[str], context: RenderContext
) -> List[TabOutput]:
    unordered: Dict[Tab, TabOutput] = {
        tab_output.tab.slug: tab_output
        # recurse -- the same way we clean a list.
        for tab_output in clean_value_list(dtype, value, context)
        if tab_output is not None
    }

    # Order based on `context.tabs`.
    return [unordered[tab] for tab in context.tabs.keys() if tab in unordered]


@clean_value.register(ParamDType.Dict)
def _(
    dtype: ParamDType.Dict, value: Dict[str, Any], context: RenderContext
) -> Dict[str, Any]:
    ret = {}
    error_agg = PromptErrorAggregator()

    for k, v in value.items():
        try:
            ret[k] = clean_value(dtype.properties[k], v, context)
        except PromptingError as err:
            error_agg.extend(err.errors)

    error_agg.raise_if_nonempty()
    return ret


@clean_value.register(ParamDType.Map)
def _(
    dtype: ParamDType.Map, value: Dict[str, Any], context: RenderContext
) -> Dict[str, Any]:
    value_dtype = dtype.value_dtype
    value_clean = partial(clean_value, value_dtype)
    return dict((k, value_clean(v, context)) for k, v in value.items())
