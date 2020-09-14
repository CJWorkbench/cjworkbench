from __future__ import annotations

import json
import marshal
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, NamedTuple, Optional, Union

import pyarrow
import pyarrow.ipc
import pyarrow.types
from cjwkernel.util import json_encode
from cjwmodule.arrow.format import parse_number_format

# Some types we can import with no conversion
from .thrift import ttypes

__all__ = [
    "ArrowTable",
    "Column",
    "ColumnType",
    "CompiledModule",
    "I18nMessage",
    "Params",
    "QuickFix",
    "QuickFixAction",
    "RenderError",
    "RenderResult",
    "Tab",
    "TableMetadata",
    "TabOutput",
    "arrow_column_to_thrift",
    "arrow_column_type_to_thrift",
    "arrow_arrow_table_to_thrift",
    "arrow_fetch_result_to_thrift",
    "arrow_params_to_thrift",
    "arrow_quick_fix_action_to_thrift",
    "arrow_quick_fix_to_thrift",
    "arrow_raw_params_to_thrift",
    "arrow_render_error_to_thrift",
    "arrow_table_metadata_to_thrift",
    "arrow_tab_to_thrift",
    "thrift_column_to_arrow",
    "thrift_column_type_to_arrow",
    "thrift_arrow_table_to_arrow",
    "thrift_fetch_result_to_arrow",
    "thrift_params_to_arrow",
    "thrift_quick_fix_action_to_arrow",
    "thrift_quick_fix_to_arrow",
    "thrift_raw_params_to_arrow",
    "thrift_render_error_to_arrow",
    "thrift_table_metadata_to_arrow",
    "thrift_tab_to_arrow",
]


def _thrift_filename_to_path(filename: str, basedir: Path) -> Path:
    if "/" in filename:
        raise ValueError("filename must not contain directories; got '%s'" % filename)
    if filename.startswith("."):
        raise ValueError("filename must not be hidden; got '%s'" % filename)
    path = basedir / filename
    if not path.is_file():
        raise ValueError("file must exist and be a regular file; got '%s'" % str(path))
    return path


@dataclass(frozen=True)
class CompiledModule:
    module_slug: str
    """
    Identifier for the module.

    This helps with log messages and debugging.
    """

    marshalled_code_object: bytes
    """
    `compile()` return value, serialied by "marshal" module.

    This can be used as: `exec(marshal.loads(marshalled_code_object))`.

    (The "marshal" module is designed specifically for building pyc files;
    that's the way we use it.)
    """

    @property
    def code_object(self) -> Any:
        return marshal.loads(self.marshalled_code_object)


class ColumnType(ABC):
    """
    Data type of a column.

    This describes how it is presented -- not how its bytes are arranged.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the type: 'text', 'number' or 'datetime'.
        """
        pass


@dataclass(frozen=True)
class ColumnTypeText(ColumnType):
    # override
    @property
    def name(self) -> str:
        return "text"


@dataclass(frozen=True)
class ColumnTypeNumber(ColumnType):
    # https://docs.python.org/3/library/string.html#format-specification-mini-language
    format: str = "{:,}"  # Python format() string -- default adds commas
    # TODO handle locale, too: format depends on it. Python will make this
    # difficult because it can't format a string in an arbitrary locale: it can
    # only do it using global variables, which we can't use.

    def __post_init__(self):
        parse_number_format(self.format)  # raise ValueError

    # override
    @property
    def name(self) -> str:
        return "number"


@dataclass(frozen=True)
class ColumnTypeDatetime(ColumnType):
    # # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    # format: str = '{}'  # Python format() string

    # # TODO handle locale, too: format depends on it. Python will make this
    # # difficult because it can't format a string in an arbitrary locale: it can
    # # only do it using global variables, which we can't use.

    # override
    @property
    def name(self) -> str:
        return "datetime"


# Aliases to help with import. e.g.:
# from cjwkernel.types import Column, ColumnType
# column = Column('A', ColumnType.Number('{:,.2f}'))
ColumnType.Text = ColumnTypeText
ColumnType.Number = ColumnTypeNumber
ColumnType.Datetime = ColumnTypeDatetime


class Column(NamedTuple):
    """
    A column definition.
    """

    name: str
    """Name of the column."""

    type: ColumnType
    """How the column data is stored and displayed to the user."""


class TableMetadata(NamedTuple):
    """Table data that will be cached for easy access."""

    n_rows: int = 0
    """Number of rows in the table."""

    columns: List[Column] = []
    """Columns -- the user-visible aspects of them, at least."""


def _pyarrow_type_to_column_type(
    dtype: pyarrow.DataType, fallback_column_type: Optional[ColumnType]
) -> ColumnType:
    if pyarrow.types.is_floating(dtype) or pyarrow.types.is_integer(dtype):
        if fallback_column_type is not None and fallback_column_type.name == "number":
            return ColumnTypeNumber(fallback_column_type.format)
        else:
            return ColumnTypeNumber()
    elif pyarrow.types.is_string(dtype) or (
        pyarrow.types.is_dictionary(dtype) and pyarrow.types.is_string(dtype.value_type)
    ):
        return ColumnTypeText()
    elif pyarrow.types.is_timestamp(dtype):
        return ColumnTypeDatetime()
    else:
        return ValueError("Unknown pyarrow type %r" % dtype)


@dataclass(frozen=True)
class ArrowTable:
    """
    Table on disk, opened and mmapped.

    A table with no rows must have a file on disk. A table with no _columns_
    is a special case: it _may_ have `table is None and path is None`, or it
    may have an empty Arrow table on disk.

    `self.table` will be populated and validated during construction.

    To pass an ArrowTable between processes, the file must be readable at the
    same `path` to both processes. If your ArrowTable isn't being shared
    between processes, you may safely delete the file at `path` immediately
    after constructing the ArrowTable.
    """

    path: Optional[Path] = None
    """
    Name of file on disk that contains data.

    If the table has columns, the file must exist.
    """

    table: Optional[pyarrow.Table] = None
    """
    Pyarrow table, loaded with mmap.

    If the table has columns, `table` must exist.
    """

    metadata: TableMetadata = field(default_factory=TableMetadata)
    """
    Metadata that agrees with `table`.

    If `table is None`, then `metadata` has no columns.
    """

    def __post_init__(self):
        """
        Raise AssertionError if arguments are obviously wrong.

        This is designed to catch obvious programming errors.
        """
        from .validate import ValidateError, validate_table_metadata

        assert (self.path is None) == (self.table is None)
        try:
            validate_table_metadata(self.table, self.metadata)
        except ValidateError as err:
            raise AssertionError("Built invalid ArrowTable: %r" % err)

    def __eq__(self, other: Any) -> bool:
        """
        Compare for table equality: same Arrow data and same metadata.

        `path` is not tested. Typical callers will use tempfiles and not care
        whether they're equal.
        """
        return (
            isinstance(other, type(self))
            and other.metadata == self.metadata
            and (
                (other.table is None and self.table is None)
                or (
                    other.table is not None
                    and self.table is not None
                    and other.table.equals(self.table)
                )
            )
        )

    @property
    def n_bytes_on_disk(self) -> int:
        """
        Return the number of bytes consumed on disk.

        Raise FileNotFoundError if the file on disk could not be read.
        """
        if self.path is None:
            return 0
        else:
            return self.path.stat().st_size

    @classmethod
    def from_untrusted_file(cls, path: Path, metadata: TableMetadata) -> ArrowTable:
        """
        Build an ArrowTable from path and metadata.

        Raise ValidateError if the file does not match expectations, Arrow
        data does not match metadata, or `path` is not a readable file. This
        scans the entire file.

        The file will be validated to ensure SECURITY.
        """
        from .validate import validate_arrow_file, validate_table_metadata

        validate_arrow_file(path)  # raise ValidateError
        # Since the file is valid, assume we can read it without error
        reader = pyarrow.ipc.open_file(path.as_posix())  # raise nothing
        table = reader.read_all()  # raise nothing
        validate_table_metadata(table, metadata)  # raise ValidateError
        return ArrowTable(path, table, metadata)

    @classmethod
    def from_trusted_file(cls, path: Path, metadata: TableMetadata) -> ArrowTable:
        """
        Build an ArrowTable from path and metadata.

        Raise AssertionError if the table does not match metadata or the file
        is not readable. (These checks are fast.)

        SECURITY: be sure this table was generated by internal tools. Untrusted
        code can generate Arrow files that do Bad Things. Read those files with
        `from_untrusted_file()`. It's a bit slower, but it's safe.
        """
        from .validate import ValidateError, validate_table_metadata

        try:
            reader = pyarrow.ipc.open_file(path.as_posix())
            table = reader.read_all()
            validate_table_metadata(table, metadata)
            return ArrowTable(path, table, metadata)
        except (pyarrow.ArrowInvalid, pyarrow.ArrowIOError, ValidateError) as err:
            raise AssertionError(
                "Called ArrowTable.from_trusted_file() incorrectly"
            ) from err

    @classmethod
    def from_zero_column_metadata(cls, metadata: TableMetadata) -> ArrowTable:
        """
        Build an ArrowTable that has no data.

        Raise ValidateError if the metadata is not no-data.
        """
        from .validate import validate_table_metadata

        validate_table_metadata(None, metadata)
        return cls(None, None, metadata)

    @classmethod
    def from_arrow_file_with_inferred_metadata(
        cls, path: Path, *, fallback_column_types: Dict[str, ColumnType] = {}
    ) -> ArrowTable:
        """
        Build from a trusted Arrow file and infer metadata.

        TODO move this function elsewhere.
        """
        # If path does not exist or is empty file, empty ArrowTable
        try:
            if path.stat().st_size == 0:
                return cls()
        except FileNotFoundError:
            return cls()

        with pyarrow.ipc.open_file(path) as reader:
            schema = reader.schema

            # if table has no columns, empty ArrowTable
            columns = [
                Column(
                    name,
                    _pyarrow_type_to_column_type(
                        dtype, fallback_column_types.get(name)
                    ),
                )
                for name, dtype in zip(schema.names, schema.types)
            ]
            if not columns:
                return cls()

            table = reader.read_all()
        n_rows = table.num_rows
        return cls(path, table, TableMetadata(n_rows, columns))


class Tab(NamedTuple):
    """Tab description."""

    slug: str
    """Tab identifier, unique in its Workflow."""

    name: str
    """Tab name, provided by the user."""


class TabOutput(NamedTuple):
    """
    Already-computed output of a tab.

    During workflow execute, the output from one tab can be used as the input to
    another. This only happens if the output was a `RenderResult` with a
    non-zero-column `table`. (The executor won't run a Step whose inputs aren't
    valid.)
    """

    tab: Tab
    """Tab that was processed."""

    table: ArrowTable
    """
    Output from the final Step in `tab`.

    This is not a RenderResult because the kernel will not render a Step if one
    of its params is a Tab whose result `.status` is not "ok".
    """


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
        raise ValueError("Unhandled ttypes.I18nArgument: %r" % value)


def _i18n_argument_to_thrift(value: Union[str, int, float]) -> ttypes.I18nArgument:
    if isinstance(value, str):
        return ttypes.I18nArgument(string_value=value)
    elif isinstance(value, int):
        return ttypes.I18nArgument(i32_value=value)
    elif isinstance(value, float):
        return ttypes.I18nArgument(double_value=value)
    else:
        raise RuntimeError("Unhandled value for I18nArgument: %r" % value)


class I18nMessage(NamedTuple):
    """Translation key and arguments."""

    id: str
    """Message ID. For instance, `modules.renamecolumns.duplicateColname`"""

    args: Dict[str, Union[int, float, str]] = {}
    """Arguments (empty if message does not need any -- which is common)."""

    source: Literal["module", "cjwmodule", None] = None
    """Where the message comes from.

    * "module": the module that raised it
    * "cjwmodule": the cjwmodule library
    * None: Workbench itself.
    """

    @classmethod
    def TODO_i18n(cls, text: str) -> I18nMessage:
        """
        Build an I18nMessage that "translates" into English only.

        The message has id "TODO_i18n" and one argument, "text", in English.
        Long-term, all these messages should disappear; but this helps us
        migrate by letting us code without worrying about translation.
        """
        return cls("TODO_i18n", {"text": text})

    @classmethod
    def trans(
        cls,
        message_id: str,
        *,
        default: str,
        args: Dict[str, Union[int, float, str]] = {},
    ) -> I18nMessage:
        """
        Build an I18nMessage, marking it for translation.

        Use this method (instead of constructing `I18nMessage` directly) when you wish to mark a string for translation. Workbench's tooling will extract messages from all `I18nMessage.trans()` calls and send them to translators.

        The `default` argument is ignored at runtime, it's only used when parsing code.
        """
        return cls(message_id, args)


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


class RawParams(NamedTuple):
    params: Dict[str, Any]


class Params(NamedTuple):
    """
    Nested data structure passed to `render()` -- includes Column/TabOutput.
    """

    params: Dict[str, Any]


class QuickFixAction(ABC):
    """Instruction for what happens when the user clicks a Quick Fix button."""


@dataclass(frozen=True)
class PrependStepQuickFixAction(QuickFixAction):
    """Instruction that upon clicking a button, we should create a Step."""

    module_slug: str
    """Module to prepend."""

    partial_params: Dict[str, Any]
    """Some params to set on the new Step (atop the module's defaults)."""


QuickFixAction.PrependStep = PrependStepQuickFixAction


class QuickFix(NamedTuple):
    """Button the user can click in response to an error message."""

    button_text: I18nMessage
    action: QuickFixAction


class RenderError(NamedTuple):
    """
    Error or warning encountered during `render()`.

    If `render()` output is a zero-column table, then its result's errors are
    "errors" -- they prevent the workflow from executing. If `render()` outputs
    columns, though, then its result's errors are "warnings" -- execution
    continues and these messages are presented to the user.
    """

    message: I18nMessage
    quick_fixes: List[QuickFix] = []


class FetchResult(NamedTuple):
    """
    The module executed a Step's fetch() without crashing.
    """

    path: Path
    """
    File storing whatever data fetch() output.

    If `path` starts and ends with Parquet's magic numbers, "PAR1", then
    fetcher will interpret `path` as tabular data. Otherwise, it will be
    treated as a file. See `fetcher/versions.py` for rationale. TODO make file
    format explicit (or nix the concept entirely).
    """

    errors: List[RenderError] = []
    """
    User-facing errors (or warnings) reported by the module.
    """


@dataclass(frozen=True)
class RenderResult:
    """
    The module executed a Step's render() without crashing.

    An result may be a user-friendly "error" -- a zero-column table and
    non-empty `errors`. Indeed, Workbench tends to catch and wrap bugs so
    they appear as RenderResult. In a sense, render cannot fail: it will
    _always_ produce a RenderResult.

    To pass a RenderResult between processes, the file must be readable at the
    same `table.path` to both processes. If your RenderResult isn't shared
    between processes, you may safely delete the file at `table.path`
    immediately after constructing `table`.
    """

    table: ArrowTable = field(default_factory=ArrowTable)
    """
    Table the Step outputs.

    If the Step output is "error, then the table must have zero columns.
    """

    errors: List[RenderError] = field(default_factory=list)
    """User-facing errors or warnings reported by the module."""

    json: Dict[str, Any] = field(default_factory=dict)
    """JSON to pass to the module's HTML, if it has HTML."""

    @property
    def status(self) -> str:
        """
        Return "ok", "error" or "unreachable".

        "ok" means there is a table as output.

        "error" means there are no table columns and error messages have been
        set by the module.

        "unreachable" means there are no table columns. (We stop rendering when
        a tab has no more columns -- hence the name, "unreachable".) Modules may
        return a result in this state, but it's usually not what the user wants.
        Modules should return error messages to help the user arrive at "ok".
        """
        if not self.table.metadata.columns:
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
    elif isinstance(value, ColumnTypeDatetime):
        return ttypes.ColumnType(datetime_type=ttypes.ColumnTypeDatetime())
    elif isinstance(value, ColumnTypeNumber):
        return ttypes.ColumnType(number_type=ttypes.ColumnTypeNumber(value.format))
    else:
        raise NotImplementedError


def arrow_column_to_thrift(value: Column) -> ttypes.Column:
    return ttypes.Column(value.name, arrow_column_type_to_thrift(value.type))


def arrow_table_metadata_to_thrift(value: TableMetadata) -> ttypes.TableMetadata:
    return ttypes.TableMetadata(
        value.n_rows, [arrow_column_to_thrift(c) for c in value.columns]
    )


def arrow_arrow_table_to_thrift(value: ArrowTable) -> ttypes.ArrowTable:
    return ttypes.ArrowTable(
        "" if value.path is None else value.path.name,
        arrow_table_metadata_to_thrift(value.metadata),
    )


def arrow_tab_to_thrift(value: Tab) -> ttypes.Tab:
    return ttypes.Tab(value.slug, value.name)


def arrow_tab_output_to_thrift(value: TabOutput) -> ttypes.Tab:
    return ttypes.TabOutput(
        arrow_tab_to_thrift(value.tab), arrow_arrow_table_to_thrift(value.table)
    )


def arrow_i18n_message_to_thrift(value: I18nMessage) -> ttypes.I18nMessage:
    return ttypes.I18nMessage(
        value.id,
        {k: _i18n_argument_to_thrift(v) for k, v in value.args.items()},
        value.source,
    )


def arrow_raw_params_to_thrift(value: RawParams) -> ttypes.RawParams:
    return ttypes.RawParams(json_encode(value.params))


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


def arrow_params_to_thrift(value: Params) -> Dict[str, ttypes.ParamValue]:
    return {k: arrow_param_value_to_thrift(v) for k, v in value.params.items()}


def arrow_quick_fix_action_to_thrift(value: QuickFixAction) -> ttypes.QuickFixAction:
    if isinstance(value, PrependStepQuickFixAction):
        return ttypes.QuickFixAction(
            prepend_step=ttypes.PrependStepQuickFixAction(
                value.module_slug, ttypes.RawParams(json_encode(value.partial_params))
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
        arrow_arrow_table_to_thrift(value.table),
        [arrow_render_error_to_thrift(e) for e in value.errors],
        "" if value.json is None else json_encode(value.json),
    )


### thrift_*_to_arrow(): decode Arrow types from Thrift
#
# They raise ValueError on cheap-to-detect semantic errors.


def thrift_column_type_to_arrow(value: ttypes.ColumnType) -> ColumnType:
    if value.text_type is not None:
        return ColumnTypeText()
    elif value.number_type is not None:
        format = value.number_type.format
        return ColumnTypeNumber(format)  # raise ValueError on invalid format
    elif value.datetime_type is not None:
        return ColumnTypeDatetime()
    else:
        raise ValueError("Unhandled Thrift object: %r" % value)


def thrift_column_to_arrow(value: ttypes.Column) -> Column:
    return Column(value.name, thrift_column_type_to_arrow(value.type))


def thrift_table_metadata_to_arrow(value: ttypes.TableMetadata) -> TableMetadata:
    return TableMetadata(
        value.n_rows, [thrift_column_to_arrow(c) for c in value.columns]
    )


def thrift_arrow_table_to_arrow(
    value: ttypes.ArrowTable, basedir: Path, trusted: bool = False
) -> ArrowTable:
    """
    Convert from a Thrift ArrowTable.

    Raise ValidateError if the file on disk cannot be read, is not sane or
    does not match metadata.

    Since Thrift is used for inter-process communication, by default we
    treat the file as untrusted. (See `from_untrusted_file()`.)
    """
    metadata = thrift_table_metadata_to_arrow(value.metadata)
    if value.filename:
        path = _thrift_filename_to_path(value.filename, basedir)
        if trusted:
            return ArrowTable.from_trusted_file(path, metadata)
        else:
            return ArrowTable.from_untrusted_file(path, metadata)
    else:
        return ArrowTable.from_zero_column_metadata(metadata)


def thrift_tab_to_arrow(value: ttypes.Tab) -> Tab:
    return Tab(value.slug, value.name)


def thrift_tab_output_to_arrow(value: ttypes.TabOutput, basedir: Path) -> TabOutput:
    return TabOutput(
        thrift_tab_to_arrow(value.tab),
        thrift_arrow_table_to_arrow(value.table, basedir),
    )


def thrift_i18n_message_to_arrow(value: ttypes.I18nMessage) -> I18nMessage:
    if value.source not in [None, "module", "cjwmodule", "cjwparse"]:
        raise ValueError("Invalid message source %r" % value.source)
    return I18nMessage(
        value.id,
        {k: _thrift_i18n_argument_to_arrow(v) for k, v in value.arguments.items()},
        value.source,
    )


def thrift_raw_params_to_arrow(value: ttypes.RawParams) -> RawParams:
    return RawParams(json.loads(value.json))


def _thrift_param_value_to_arrow(value: ttypes.ParamValue, basedir: Path) -> ParamValue:
    if value.string_value is not None:
        return value.string_value
    elif value.integer_value is not None:
        return value.integer_value
    elif value.float_value is not None:
        return value.float_value
    elif value.boolean_value is not None:
        return value.boolean_value
    elif value.column_value is not None:
        return thrift_column_to_arrow(value.column_value)
    elif value.tab_value is not None:
        return thrift_tab_output_to_arrow(value.tab_value, basedir)
    elif value.list_value is not None:
        return [_thrift_param_value_to_arrow(v, basedir) for v in value.list_value]
    elif value.map_value is not None:
        return {
            k: _thrift_param_value_to_arrow(v, basedir)
            for k, v in value.map_value.items()
        }
    elif value.filename_value is not None:
        return _thrift_filename_to_path(value.filename_value, basedir)
    else:
        return None


def thrift_params_to_arrow(
    value: Dict[str, ttypes.ParamsValue], basedir: Path
) -> Params:
    return Params(
        {k: _thrift_param_value_to_arrow(v, basedir) for k, v in value.items()}
    )


def thrift_quick_fix_action_to_arrow(value: ttypes.QuickFixAction) -> QuickFixAction:
    if value.prepend_step is not None:
        return PrependStepQuickFixAction(
            value.prepend_step.module_slug,
            json.loads(value.prepend_step.partial_params.json),
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


def thrift_render_result_to_arrow(
    value: ttypes.RenderResult, basedir: Path
) -> RenderResult:
    return RenderResult(
        thrift_arrow_table_to_arrow(value.table, basedir),
        [thrift_render_error_to_arrow(e) for e in value.errors],
        json.loads(value.json) if value.json else None,
    )
