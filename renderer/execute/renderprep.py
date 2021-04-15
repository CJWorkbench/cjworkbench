import re
import iso8601
from contextlib import ExitStack
from dataclasses import dataclass
from functools import partial, singledispatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from cjwkernel.types import (
    Column,
    ColumnType,
    LoadedRenderResult,
    Params,
    Tab,
    TabOutput,
)

from cjwkernel.util import tempfile_context
from cjwstate import s3
from cjwstate.models import UploadedFile
from cjwstate.modules.param_dtype import ParamDType
from .types import StepResult, TabCycleError, TabOutputUnreachableError, PromptingError


FilesystemUnsafeChars = re.compile("[^-_.,()a-zA-Z0-9]")
SingleDigitMonthOrDay = re.compile(r".*\b\d\b.*")


def _validate_iso8601_string(s):
    try:
        iso8601.parse_date(s)
    except iso8601.ParseError:
        raise ValueError("Invalid ISO8601 date")
    # but of course, that would be too easy. iso8601.parse_date() allows invalid
    # dates:
    if " " in s:
        raise ValueError("Date and time must be separated by T")
    if SingleDigitMonthOrDay.match(s):
        raise ValueError("Month and day must have a leading 0")


PromptingErrorSubtype = Union[
    PromptingError.WrongColumnType,
    PromptingError.CannotCoerceValueToNumber,
    PromptingError.CannotCoerceValueToTimestamp,
]


class PromptErrorAggregator:
    def __init__(self):
        self.groups = {}  # found_type => { wanted_types => column_names }
        self.ungrouped_errors = []
        # Errors are first-come-first-reported, per type. We get that because
        # Python 3.7+ dicts iterate in insertion order.

    def extend(self, errors: List[PromptingErrorSubtype]) -> None:
        for error in errors:
            self.add(error)

    def add(self, error: PromptingErrorSubtype) -> None:
        if isinstance(error, PromptingError.WrongColumnType):
            if "text" in error.wanted_types:
                found_type = None
            else:
                found_type = error.found_type
            group = self.groups.setdefault(found_type, {})
            names = group.setdefault(error.wanted_types, [])
            for name in error.column_names:
                if name not in names:
                    names.append(name)
        else:
            self.ungrouped_errors.append(error)

    def raise_if_nonempty(self):
        if not self.groups and not self.ungrouped_errors:
            return

        errors = []
        for found_type, group in self.groups.items():
            for wanted_types, column_names in group.items():
                errors.append(
                    PromptingError.WrongColumnType(
                        column_names, found_type, wanted_types
                    )
                )
        errors.extend(self.ungrouped_errors)
        raise PromptingError(errors)


@dataclass(frozen=True)
class _TabData:
    tab: Tab
    result: Optional[LoadedRenderResult]

    @property
    def slug(self) -> str:
        return self.tab.slug


class RenderContext:
    def __init__(
        self,
        step_id: int,
        input_table_columns: List[Column],
        # assume tab_results keys are ordered the way the user ordered the tabs.
        tab_results: Dict[Tab, Optional[StepResult]],
        basedir: Path,
        exit_stack: ExitStack,
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
        self.step_id = step_id
        self.input_table_columns = input_table_columns
        self.tabs: Dict[str, _TabData] = {
            k.slug: _TabData(k, v) for k, v in tab_results.items()
        }
        self.basedir = basedir
        self.exit_stack = exit_stack
        self.params = params

    def output_columns_for_tab_parameter(self, tab_parameter):
        if tab_parameter is None:
            # Common case: param selects from the input table
            return {c.name: c for c in self.input_table_columns}

        # Rare case: there's a "tab" parameter, and the column selector is
        # selecting from _that_ tab's output columns.

        # valid schema means no KeyError
        tab_slug = self.params[tab_parameter]

        try:
            tab_data = self.tabs[tab_slug]
        except KeyError:
            # Tab does not exist
            return {}
        if tab_data.result is None or not tab_data.result.columns:
            # Tab has a cycle or other error.
            return {}

        return {c.name: c for c in tab_data.result.columns}


def get_param_values(
    schema: ParamDType.Dict, params: Dict[str, Any], context: RenderContext
) -> Params:
    """Convert `params` to a dict we'll pass to a module `render()` function.

    Concretely:

        * `Tab` parameters become Optional[TabOutput] (declared here)
        * Eliminate missing `Tab`s: they'll be `None`
        * Raise `TabCycleError` if a chosen Tab has not been rendered
        * `column` parameters become '' if they aren't input columns
        * `multicolumn` parameters lose values that aren't input columns
        * Raise `PromptingError` if a chosen column is of the wrong type
          (so the caller can build errors and quickfixes)

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
    """Ensure `value` fits the Params dict `render()` expects.

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


_InverseOperations = {
    "cell_is_not_empty": "cell_is_empty",
    "cell_is_not_null": "cell_is_null",
    "number_is_not": "number_is",
    "text_does_not_contain": "text_contains",
    "text_is_not": "text_is",
    "timestamp_is_not": "timestamp_is",
}


def _clean_condition_recursively(
    value: Dict[str, Any], column_types: Dict[str, str]
) -> Tuple[Optional[Dict[str, Any]], List[PromptingError]]:
    if value["operation"] == "":
        return None, []
    elif value["operation"] in {"and", "or"}:
        errors = []
        conditions = []
        for entry in value["conditions"]:
            clean_condition, clean_errors = _clean_condition_recursively(
                entry, column_types
            )
            errors.extend(clean_errors)
            if clean_condition is not None:
                conditions.append(clean_condition)

        if len(conditions) == 0:
            return None, errors
        elif len(conditions) == 1:
            return conditions[0], errors
        else:
            return {"operation": value["operation"], "conditions": conditions}, errors
    elif value["operation"] in _InverseOperations:
        clean_condition, errors = _clean_condition_recursively(
            {**value, "operation": _InverseOperations[value["operation"]]}, column_types
        )
        if clean_condition is None:
            return None, errors
        else:
            return {"operation": "not", "condition": clean_condition}, errors
    else:
        clean_condition = None
        errors = []

        if value["column"] not in column_types:
            # No valid column selected.
            #
            # It would be nice to warn on invalid column ... but [2020-11-16]
            # we don't have a way to do that, because the default params are
            # empty and we validate them. More-general problem of the
            # same flavor: https://www.pivotaltracker.com/story/show/174473146
            pass
        else:
            column_type = column_types[value["column"]]
            if value["operation"].startswith("text"):
                if column_type != "text":
                    errors.append(
                        PromptingError.WrongColumnType(
                            [value["column"]], None, frozenset(["text"])
                        )
                    )
                else:
                    clean_condition = value

            elif value["operation"].startswith("number"):
                if column_type != "number":
                    errors.append(
                        PromptingError.WrongColumnType(
                            [value["column"]], column_type, frozenset(["number"])
                        )
                    )
                try:
                    number_value = float(value["value"])
                except ValueError:
                    errors.append(
                        PromptingError.CannotCoerceValueToNumber(value["value"])
                    )

                if not errors:
                    clean_condition = {
                        "operation": value["operation"],
                        "column": value["column"],
                        "value": number_value,
                    }

            elif value["operation"].startswith("timestamp"):
                if column_type != "timestamp":
                    errors.append(
                        PromptingError.WrongColumnType(
                            [value["column"]], column_type, frozenset(["timestamp"])
                        )
                    )
                try:
                    _validate_iso8601_string(value["value"])
                except ValueError:
                    errors.append(
                        PromptingError.CannotCoerceValueToTimestamp(value["value"])
                    )

                if not errors:
                    clean_condition = {
                        "operation": value["operation"],
                        "column": value["column"],
                        "value": value["value"],
                    }

            else:
                assert value["operation"].startswith("cell")
                clean_condition = {
                    "operation": value["operation"],
                    "column": value["column"],
                }

        return clean_condition, errors


def _column_type_name(column_type: ColumnType) -> str:
    if isinstance(column_type, ColumnType.Text):
        return "text"
    elif isinstance(column_type, ColumnType.Date):
        return "date"
    elif isinstance(column_type, ColumnType.Number):
        return "number"
    elif isinstance(column_type, ColumnType.Timestamp):
        return "timestamp"
    else:
        raise ValueError("Unhandled column type %r" % column_type)


@clean_value.register(ParamDType.Condition)
def _(
    dtype: ParamDType.Condition, value: Dict[str, Any], context: RenderContext
) -> Optional[Dict[str, Any]]:
    condition, errors = _clean_condition_recursively(
        value,
        {
            column.name: _column_type_name(column.type)
            for column in context.input_table_columns
        },
    )
    error_agg = PromptErrorAggregator()
    for error in errors:
        error_agg.add(error)
    error_agg.raise_if_nonempty()
    return condition


@clean_value.register(ParamDType.File)
def _(
    dtype: ParamDType.File, value: Optional[str], context: RenderContext
) -> Optional[Path]:
    """Convert a `file` String-encoded UUID to a tempfile `pathlib.Path`.

    The return value:

    * Points to a temporary file containing all bytes
    * Has the same suffix as the originally-uploaded file
    * Will have its file deleted when it goes out of scope

    If the file is in the database but does not exist on s3, return `None`.
    """
    if value is None:
        return None
    try:
        uploaded_file = UploadedFile.objects.get(uuid=value, step_id=context.step_id)
    except UploadedFile.DoesNotExist:
        return None

    # UploadedFile.name may not be POSIX-compliant. We want the filename to
    # have the same suffix as the original: that helps with filetype
    # detection. We also put the UUID in the name so debug messages help
    # devs find the original file.
    safe_name = FilesystemUnsafeChars.sub("-", uploaded_file.name)
    path = context.exit_stack.enter_context(
        tempfile_context(
            prefix="file-",
            suffix=(uploaded_file.uuid + "-" + safe_name),
            dir=context.basedir,
        )
    )
    try:
        # Overwrite the file
        s3.download(s3.UserFilesBucket, uploaded_file.key, path)
        return path
    except FileNotFoundError:
        # tempfile will be deleted by context.exit_stack
        return None


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
    if not tab_result.columns:
        raise TabOutputUnreachableError

    return TabOutput(tab_data.tab, table_filename=tab_result.path.name)


@clean_value.register(ParamDType.Column)
def _(dtype: ParamDType.Column, value: str, context: RenderContext) -> str:
    valid_columns = context.output_columns_for_tab_parameter(dtype.tab_parameter)
    if value not in valid_columns:
        return ""  # Null column

    column = valid_columns[value]
    if dtype.column_types and _column_type_name(column.type) not in dtype.column_types:
        if "text" in dtype.column_types:
            found_type = None
        else:
            found_type = _column_type_name(column.type)
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

        if (
            dtype.column_types
            and _column_type_name(column.type) not in dtype.column_types
        ):
            if "text" in dtype.column_types:
                found_type = None
            else:
                found_type = _column_type_name(column.type)
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
