from __future__ import annotations

import marshal
from pathlib import Path
from typing import Any, Dict, List, Literal, NamedTuple, Union

import pyarrow
import pyarrow.ipc
import pyarrow.types
from cjwmodule.types import (
    FetchResult,
    I18nMessage,
    QuickFix,
    QuickFixAction,
    RenderError,
)

# Some types we can import with no conversion
from .thrift import ttypes

__all__ = [
    "Column",
    "ColumnType",
    "CompiledModule",
    "QuickFix",
    "QuickFixAction",
    "RenderError",
    "RenderResult",
    "Tab",
    "TableMetadata",
    "TabOutput",
    "arrow_fetch_result_to_thrift",
    "arrow_quick_fix_action_to_thrift",
    "arrow_quick_fix_to_thrift",
    "arrow_render_error_to_thrift",
    "arrow_tab_to_thrift",
    "pydict_to_thrift_json_object",
    "thrift_fetch_result_to_arrow",
    "thrift_json_object_to_pydict",
    "thrift_quick_fix_action_to_arrow",
    "thrift_quick_fix_to_arrow",
    "thrift_render_error_to_arrow",
    "thrift_tab_to_arrow",
]


class ColumnTypeText(NamedTuple):
    pass


class ColumnTypeNumber(NamedTuple):
    format: str = "{:,}"
    """Python format() string.

    The default value formats a float with commas as thousands separators.

    TODO handle locale, too: format depends on it.
    """


class ColumnTypeTimestamp(NamedTuple):
    pass


class ColumnTypeDate(NamedTuple):
    unit: Literal["day", "week", "month", "quarter", "year"]


ColumnType = Union[
    ColumnTypeText, ColumnTypeNumber, ColumnTypeTimestamp, ColumnTypeDate
]
"""
Data type of a column.

This describes how it is presented -- not how its bytes are arranged.
"""

# Aliases to help with import. e.g.:
# from cjwmodule.types import Column, ColumnType
# column = Column('A', ColumnType.Number('{:,.2f}'))
ColumnType.Text = ColumnTypeText
ColumnType.Number = ColumnTypeNumber
ColumnType.Timestamp = ColumnTypeTimestamp
ColumnType.Date = ColumnTypeDate


class Column(NamedTuple):
    """A column definition."""

    name: str
    """Name of the column."""

    type: ColumnType
    """How the column data is stored and displayed to the user."""


def _thrift_filename_to_path(filename: str, basedir: Path) -> Path:
    if "/" in filename or "\\" in filename:
        raise ValueError(
            "filename must not include directory names; got '%s'" % filename
        )
    if filename.startswith("."):
        raise ValueError("filename must not be hidden; got '%s'" % filename)

    path = basedir / filename
    try:
        is_regular = path.is_file()
    except FileNotFoundError:
        is_regular = False
    if not is_regular:
        raise ValueError("file must exist and be a regular file; got '%s'" % filename)

    return path


class CompiledModule(NamedTuple):
    module_slug: str
    """Identifier for the module.

    This helps with log messages and debugging.
    """

    marshalled_code_object: bytes
    """`compile()` return value, serialied by "marshal" module.

    This can be used as: `exec(marshal.loads(marshalled_code_object))`.

    (The "marshal" module is designed specifically for building pyc files;
    that's the way we use it.)
    """

    module_spec_dict: Dict[str, Any]
    """Python dict the module can parse into a cjwmodule.spec.types.ModuleSpec.

    It's a bit of a hack that we parse the spec every time a module is invoked.
    But [2021-04-19] no need to optimize prematurely....
    """

    @property
    def code_object(self) -> Any:
        return marshal.loads(self.marshalled_code_object)


class TableMetadata(NamedTuple):
    """Table data that will be cached for easy access."""

    n_rows: int = 0
    """Number of rows in the table."""

    columns: List[Column] = []
    """Columns -- the user-visible aspects of them, at least."""


class Tab(NamedTuple):
    """Tab description."""

    slug: str
    """Tab identifier, unique in its Workflow."""

    name: str
    """Tab name, provided by the user."""


class TabOutput(NamedTuple):
    """Already-computed output of a tab.

    During workflow execute, the output from one tab can be used as the input to
    another. This only happens if the tab executed successfully. (The executor
    won't render a Step whose inputs aren't valid.)
    """

    tab: Tab
    """Tab that was processed."""

    table_filename: str
    """Output from the final Step in `tab`."""


def _thrift_i18n_argument_to_arrow(
    value: ttypes.I18nArgument,
) -> Union[str, int, float]:
    if value.string_value is not None:
        return value.string_value
    elif value.i32_value is not None:
        return value.i32_value
    elif value.double_value is not None:
        return value.double_value
    else:
        raise ValueError("Unhandled ttypes.I18nArgument: %r" % (value,))


def _i18n_argument_to_thrift(value: Union[str, int, float]) -> ttypes.I18nArgument:
    if isinstance(value, str):
        return ttypes.I18nArgument(string_value=value)
    elif isinstance(value, int):
        return ttypes.I18nArgument(i32_value=value)
    elif isinstance(value, float):
        return ttypes.I18nArgument(double_value=value)
    else:
        raise RuntimeError("Unhandled value for I18nArgument: %r" % (value,))


ParamValue = Union[
    None,
    str,
    int,
    float,
    bool,
    Column,
    TabOutput,
    List[Any],  # should be List[ParamValue]
    Dict[str, Any],  # should be Dict[str, ParamValue]
]


class RenderResult(NamedTuple):
    errors: List[RenderError] = []
    json: Dict[str, Any] = {}


class LoadedRenderResult(NamedTuple):
    """A RenderResult that is loaded in memory.

    The table and columns may be empty, if the status is "error" or
    "unreachable".
    """

    path: Path
    table: pyarrow.Table
    columns: List[Column]
    errors: List[RenderError]
    json: Dict[str, Any]

    @classmethod
    def unreachable(cls, path: Path) -> LoadedRenderResult:
        return LoadedRenderResult(
            path=path, table=pyarrow.table({}), columns=[], errors=[], json={}
        )

    @classmethod
    def from_errors(cls, path: Path, errors: List[RenderError]) -> LoadedRenderResult:
        return LoadedRenderResult(
            path=path, table=pyarrow.table({}), columns=[], errors=errors, json={}
        )

    @property
    def status(self) -> Literal["ok", "error", "unreachable"]:
        if not self.columns:
            if self.errors:
                return "error"
            else:
                return "unreachable"
        else:
            return "ok"


### arrow_*_to_thrift(): encode Arrow types as Thrift


def arrow_column_type_to_thrift(value: ColumnType) -> ttypes.ColumnType:
    if isinstance(value, ColumnTypeText):
        return ttypes.ColumnType(text_type=ttypes.ColumnTypeText())
    elif isinstance(value, ColumnTypeTimestamp):
        return ttypes.ColumnType(timestamp_type=ttypes.ColumnTypeTimestamp())
    elif isinstance(value, ColumnTypeNumber):
        return ttypes.ColumnType(
            number_type=ttypes.ColumnTypeNumber(format=value.format)
        )
    elif isinstance(value, ColumnTypeDate):
        unit = {
            "day": ttypes.ColumnTypeDateUnit.DAY,
            "week": ttypes.ColumnTypeDateUnit.WEEK,
            "month": ttypes.ColumnTypeDateUnit.MONTH,
            "quarter": ttypes.ColumnTypeDateUnit.QUARTER,
            "year": ttypes.ColumnTypeDateUnit.YEAR,
        }[value.unit]
        return ttypes.ColumnType(date_type=ttypes.ColumnTypeDate(unit=unit))
    else:
        raise NotImplementedError


def arrow_column_to_thrift(value: Column) -> ttypes.Column:
    return ttypes.Column(value.name, arrow_column_type_to_thrift(value.type))


def arrow_tab_to_thrift(value: Tab) -> ttypes.Tab:
    return ttypes.Tab(value.slug, value.name)


def arrow_tab_output_to_thrift(value: TabOutput) -> ttypes.Tab:
    return ttypes.TabOutput(
        arrow_tab_to_thrift(value.tab),
        table_filename=value.table_filename,
    )


def arrow_i18n_message_to_thrift(value: I18nMessage) -> ttypes.I18nMessage:
    return ttypes.I18nMessage(
        value.id,
        {k: _i18n_argument_to_thrift(v) for k, v in value.arguments.items()},
        value.source,
    )


def arrow_param_value_to_thrift(value: ParamValue) -> ttypes.ParamValue:
    PV = ttypes.ParamValue

    if value is None:
        return PV()  # a Thrift union with no value
    elif isinstance(value, str):
        # string, file, enum
        return PV(string_value=value)
    elif isinstance(value, int) and not isinstance(value, bool):
        return PV(integer_value=value)
    elif isinstance(value, float):
        return PV(float_value=value)
    elif isinstance(value, bool):
        # boolean, enum
        return PV(boolean_value=value)
    elif isinstance(value, Column):
        return PV(column_value=arrow_column_to_thrift(value))
    elif isinstance(value, TabOutput):
        return PV(tab_value=arrow_tab_output_to_thrift(value))
    elif isinstance(value, list):
        # list, multicolumn, multitab, multichartseries
        return PV(list_value=[arrow_param_value_to_thrift(v) for v in value])
    elif isinstance(value, dict):
        # map, dict
        return PV(
            map_value={k: arrow_param_value_to_thrift(v) for k, v in value.items()}
        )
    elif isinstance(value, Path):
        return PV(filename_value=value.name)
    else:
        raise RuntimeError("Unhandled value %r" % value)


def arrow_quick_fix_action_to_thrift(value: QuickFixAction) -> ttypes.QuickFixAction:
    if isinstance(value, QuickFixAction.PrependStep):
        return ttypes.QuickFixAction(
            prepend_step=ttypes.PrependStepQuickFixAction(
                value.module_slug, pydict_to_thrift_json_object(value.partial_params)
            )
        )
    else:
        raise NotImplementedError


def arrow_quick_fix_to_thrift(value: QuickFix) -> ttypes.QuickFix:
    return ttypes.QuickFix(
        arrow_i18n_message_to_thrift(value.button_text),
        arrow_quick_fix_action_to_thrift(value.action),
    )


def arrow_render_error_to_thrift(value: RenderError) -> ttypes.RenderError:
    return ttypes.RenderError(
        arrow_i18n_message_to_thrift(value.message),
        [arrow_quick_fix_to_thrift(qf) for qf in value.quick_fixes],
    )


def arrow_fetch_result_to_thrift(value: FetchResult) -> ttypes.FetchResult:
    return ttypes.FetchResult(
        value.path.name, [arrow_render_error_to_thrift(e) for e in value.errors]
    )


def arrow_render_result_to_thrift(value: RenderResult) -> ttypes.RenderResult:
    return ttypes.RenderResult(
        errors=[arrow_render_error_to_thrift(e) for e in value.errors],
        json=pydict_to_thrift_json_object(value.json),
    )


### thrift_*_to_arrow(): decode Arrow types from Thrift
#
# They raise ValueError on cheap-to-detect semantic errors.


def thrift_tab_to_arrow(value: ttypes.Tab) -> Tab:
    return Tab(value.slug, value.name)


def thrift_tab_output_to_arrow(value: ttypes.TabOutput) -> TabOutput:
    return TabOutput(thrift_tab_to_arrow(value.tab), value.table_filename)


def thrift_i18n_message_to_arrow(value: ttypes.I18nMessage) -> I18nMessage:
    if value.source not in [None, "module", "cjwmodule", "cjwparse"]:
        raise ValueError("Invalid message source %r" % value.source)
    return I18nMessage(
        value.id,
        {k: _thrift_i18n_argument_to_arrow(v) for k, v in value.arguments.items()},
        value.source,
    )


def _thrift_json_to_python(value: ttypes.Json) -> Any:
    if value.string_value is not None:
        return value.string_value
    elif value.int64_value is not None:
        return value.int64_value
    elif value.number_value is not None:
        return value.number_value
    elif value.boolean_value is not None:
        return value.boolean_value
    elif value.array_value is not None:
        return [_thrift_json_to_python(v) for v in value.array_value]
    elif value.object_value is not None:
        return {k: _thrift_json_to_python(v) for k, v in value.object_value.items()}
    else:
        return None


def thrift_json_object_to_pydict(value: Dict[str, ttypes.Json]) -> Dict[str, Any]:
    return {k: _thrift_json_to_python(v) for k, v in value.items()}


def _python_to_thrift_json(value: Any) -> ttypes.Json:
    if value is None:
        return ttypes.Json()
    elif isinstance(value, str):
        return ttypes.Json(string_value=value)
    elif isinstance(value, bool):  # before int! Python bool is subclass of int
        return ttypes.Json(boolean_value=value)
    elif isinstance(value, int):
        return ttypes.Json(int64_value=value)
    elif isinstance(value, float):
        return ttypes.Json(number_value=value)
    elif isinstance(value, list):
        return ttypes.Json(array_value=[_python_to_thrift_json(v) for v in value])
    elif isinstance(value, dict):
        return ttypes.Json(
            object_value={k: _python_to_thrift_json(v) for k, v in value.items()}
        )
    else:
        raise ValueError("Invalid JSON-ish value: %r" % (value,))


def pydict_to_thrift_json_object(pydict: Dict[str, Any]) -> Dict[str, ttypes.Json]:
    return {k: _python_to_thrift_json(v) for k, v in pydict.items()}


def thrift_quick_fix_action_to_arrow(value: ttypes.QuickFixAction) -> QuickFixAction:
    if value.prepend_step is not None:
        return QuickFixAction.PrependStep(
            value.prepend_step.module_slug,
            thrift_json_object_to_pydict(value.prepend_step.partial_params),
        )
    else:
        raise ValueError("Invalid QuickFixAction")


def thrift_quick_fix_to_arrow(value: ttypes.QuickFix) -> QuickFix:
    return QuickFix(
        thrift_i18n_message_to_arrow(value.button_text),
        thrift_quick_fix_action_to_arrow(value.action),
    )


def thrift_render_error_to_arrow(value: ttypes.RenderError) -> RenderError:
    return RenderError(
        thrift_i18n_message_to_arrow(value.message),
        [thrift_quick_fix_to_arrow(qf) for qf in value.quick_fixes],
    )


def thrift_fetch_result_to_arrow(
    value: ttypes.FetchResult, basedir: Path
) -> FetchResult:
    path = _thrift_filename_to_path(value.filename, basedir)
    return FetchResult(path, [thrift_render_error_to_arrow(e) for e in value.errors])


def thrift_render_result_to_arrow(value: ttypes.RenderResult) -> RenderResult:
    return RenderResult(
        errors=[thrift_render_error_to_arrow(e) for e in value.errors],
        json=thrift_json_object_to_pydict(value.json),
    )
