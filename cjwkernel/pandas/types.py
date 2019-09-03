# LEGACY types. TODO migrate most of these to cjwkernel.types.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
import json
from string import Formatter
from typing import Any, Dict, Iterable, List, Optional, Union
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
import pyarrow
from .validate import validate_dataframe
from .. import types as atypes


class ColumnType(ABC):
    """
    Data type of a column.

    This describes how it is presented -- not how its bytes are arranged.
    """

    @abstractmethod
    def format_series(self, series: pd.Series) -> pd.Series:
        """
        Convert a Series to a str Series.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the type: 'text', 'number' or 'datetime'.
        """

    @abstractmethod
    def to_arrow(self) -> atypes.ColumnType:
        """
        The lower-level type this type wraps.
        """

    @staticmethod
    def class_from_dtype(dtype) -> type:
        """
        Determine ColumnType class, based on pandas/numpy `dtype`.
        """
        if is_numeric_dtype(dtype):
            return ColumnType.NUMBER
        elif is_datetime64_dtype(dtype):
            return ColumnType.DATETIME
        elif dtype == object or dtype == "category":
            return ColumnType.TEXT
        else:
            raise ValueError(f"Unknown dtype: {dtype}")

    @classmethod
    def from_dtype(cls, dtype) -> ColumnType:
        """
        Build a ColumnType based on pandas/numpy `dtype`.

        If the type is Number or Datetime, it will have an "empty"
        (auto-generated) format.
        """
        return cls.class_from_dtype(dtype)()

    @classmethod
    def from_arrow(cls, value: atypes.ColumnType) -> ColumnType:
        """
        Wrap a lower-level ColumnType.
        """
        if isinstance(value, atypes.ColumnType.Text):
            return ColumnType.TEXT()
        elif isinstance(value, atypes.ColumnType.Number):
            return ColumnType.NUMBER(value.format)
        elif isinstance(value, atypes.ColumnType.Datetime):
            return ColumnType.DATETIME()
        else:
            raise RuntimeError("Unhandled value %r" % value)


@dataclass(frozen=True)
class ColumnTypeText(ColumnType):
    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        return series

    # override
    @property
    def name(self) -> str:
        return "text"

    # override
    def to_arrow(self) -> atypes.ColumnType.Text:
        return atypes.ColumnType.Text()


class NumberFormatter:
    """
    Utility to convert int and float to str.

    Usage:

        formatter = NumberFormatter('${:,.2f}')
        formatter.format(1234.56)  # => "$1,234.56"

    This is similar to Python `format()` but different:

    * It allows formatting float as int: `NumberFormatter('{:d}').format(0.1)`
    * It disallows "conversions" (e.g., `{!r:s}`)
    * It disallows variable name/numbers (e.g., `{1:d}`, `{value:d}`)
    * It raises ValueError on construction if format is imperfect
    * Its `.format()` method always succeeds
    """

    _IntTypeSpecifiers = set("bcdoxXn")
    """
    Type names that operate on integer (as opposed to float).

    Python `format()` auto-converts int to float, but it doesn't auto-convert
    float to int. Workbench does auto-convert float to int: any format that
    works for one Number must work for all Numbers.
    """

    def __init__(self, format_s: str):
        if not isinstance(format_s, str):
            raise ValueError("Format must be str")

        # parts: a list of (literal_text, field_name, format_spec, conversion)
        #
        # The "literal_text" always comes _before_ the field. So we end up
        # with three possibilities:
        #
        #    "prefix{}suffix": [(prefix, "", "", ""), (suffix, None...)]
        #    "prefix{}": [(prefix, "", "", '")]
        #    "{}suffix": [("", "", "", ""), (suffix, None...)]
        parts = list(Formatter().parse(format_s))

        if len(parts) > 2 or len(parts) == 2 and parts[1][1] is not None:
            raise ValueError("Can only format one number")

        if not parts or parts[0][1] is None:
            raise ValueError('Format must look like "{:...}"')

        if parts[0][1] != "":
            raise ValueError("Field names or numbers are not allowed")

        if parts[0][3] is not None:
            raise ValueError("Field converters are not allowed")

        self._prefix = parts[0][0]
        self._format_spec = parts[0][2]
        if len(parts) == 2:
            self._suffix = parts[1][0]
        else:
            self._suffix = ""
        self._need_int = (
            self._format_spec and self._format_spec[-1] in self._IntTypeSpecifiers
        )

        # Test it!
        #
        # A reading of cpython 3.7 Python/formatter_unicode.c
        # parse_internal_render_format_spec() suggests the following unobvious
        # details:
        #
        # * Python won't parse a format spec unless you're formatting a number
        # * _PyLong_FormatAdvancedWriter() accepts a superset of the formats
        #   _PyFloat_FormatAdvancedWriter() accepts. (Workbench accepts that
        #   superset.)
        #
        # Therefore, if we can format an int, the format is valid.
        format(1, self._format_spec)

    def format(self, value: Union[int, float]) -> str:
        if self._need_int:
            value = int(value)
        else:
            # Format float64 _integers_ as int. For instance, '3.0' should be
            # formatted as though it were the int, '3'.
            #
            # Python would normally format '3.0' as '3.0' by default; that's
            # not acceptable to us because we can't write a JavaScript
            # formatter that would do the same thing. (Javascript doesn't
            # distinguish between float and int.)
            int_value = int(value)
            if int_value == value:
                value = int_value

        return self._prefix + format(value, self._format_spec) + self._suffix


@dataclass(frozen=True)
class ColumnTypeNumber(ColumnType):
    # https://docs.python.org/3/library/string.html#format-specification-mini-language
    format: str = "{:,}"  # Python format() string -- default adds commas
    # TODO handle locale, too: format depends on it. Python will make this
    # difficult because it can't format a string in an arbitrary locale: it can
    # only do it using global variables, which we can't use.

    def __post_init__(self):
        formatter = NumberFormatter(self.format)  # raises ValueError
        object.__setattr__(self, "_formatter", formatter)

    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        ret = series.map(self._formatter.format, na_action="ignore")
        # Pandas will still think all-NA is number.
        if is_numeric_dtype(ret):
            ret = ret.astype(object)
        return ret

    # override
    @property
    def name(self) -> str:
        return "number"

    # override
    def to_arrow(self) -> atypes.ColumnType.Number:
        return atypes.ColumnType.Number(self.format)


@dataclass(frozen=True)
class ColumnTypeDatetime(ColumnType):
    # # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    # format: str = '{}'  # Python format() string

    # # TODO handle locale, too: format depends on it. Python will make this
    # # difficult because it can't format a string in an arbitrary locale: it can
    # # only do it using global variables, which we can't use.

    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        return series.dt.strftime("%FT%T.%fZ").replace("NaT", np.nan)

    # override
    @property
    def name(self) -> str:
        return "datetime"

    # override
    def to_arrow(self) -> atypes.ColumnType.Datetime:
        return atypes.ColumnType.Datetime()


# Aliases to help with import. e.g.:
# from cjwkernel.pandas.types import Column, ColumnType
# column = Column('A', ColumnType.NUMBER('{:,.2f}'))
ColumnType.TEXT = ColumnTypeText
ColumnType.NUMBER = ColumnTypeNumber
ColumnType.DATETIME = ColumnTypeDatetime

ColumnType.TypeLookup = {
    "text": ColumnType.TEXT,
    "number": ColumnType.NUMBER,
    "datetime": ColumnType.DATETIME,
}


@dataclass(frozen=True)
class Column:
    """
    A column definition.
    """

    name: str  # Name of the column
    type: ColumnType  # How it's displayed

    def to_dict(self):
        return {"name": self.name, "type": self.type.name, **asdict(self.type)}

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> Column:
        return cls.from_kwargs(**d)

    @classmethod
    def from_kwargs(cls, name: str, type: str, **column_type_kwargs) -> ColumnType:
        type_cls = ColumnType.TypeLookup[type]
        return Column(name, type_cls(**column_type_kwargs))

    @classmethod
    def from_arrow(cls, value: atypes.Column) -> Column:
        return cls(value.name, ColumnType.from_arrow(value.type))

    def to_arrow(self) -> atypes.Column:
        return atypes.Column(self.name, self.type.to_arrow())


@dataclass(frozen=True)
class TableShape:
    """
    The rows and columns of a table -- devoid of data.
    """

    nrows: int
    """Number of rows of data."""

    columns: List[Column]
    """Columns."""

    @classmethod
    def from_arrow(cls, value: atypes.TableMetadata) -> TableShape:
        return cls(value.n_rows, [Column.from_arrow(c) for c in value.columns])

    def to_arrow(self) -> atypes.TableMetadata:
        return atypes.TableMetadata(self.nrows, [c.to_arrow() for c in self.columns])


@dataclass(frozen=True)
class StepResultShape:
    """
    Low-RAM metadata about a ProcessResult.
    """

    status: str
    """Status: one of 'ok', 'error' or 'unreachable'."""

    table_shape: TableShape
    """
    Columns and number of rows in the result.

    If `status != 'ok'`, then `nrows == 0 && columns == []`.
    """


@dataclass(frozen=True)
class RenderColumn:
    """
    Column presented to a render() function in its `input_columns` argument.

    A column has a `name` and a `type`. The `type` is one of "number", "text"
    or "datetime".
    """

    name: str
    """Column name in the DataFrame."""

    type: str
    """'number', 'text' or 'datetime'."""

    format: Optional[str]
    """
    Format string for converting the given column to string.

    >>> column = RenderColumn('A', 'number', '{:,d} bottles of beer')
    >>> column.format.format(1234)
    '1,234 bottles of beer'
    """


@dataclass(frozen=True)
class TabOutput:
    """
    Tab data presented to a render() function.

    A tab has `slug` (JS-side ID), `name` (user-assigned tab name), `dataframe`
    (pandas.DataFrame), and `columns` (dict of `RenderColumn`, keyed by each
    column in `dataframe.columns`.)

    `columns` is designed to mirror the `input_columns` argument to render().
    It's a Dict[str, RenderColumn].
    """

    slug: str
    """
    Tab slug (permanent ID, unique in this Workflow, that leaks to the user).
    """

    name: str
    """Tab name visible to the user and editable by the user."""

    columns: Dict[str, RenderColumn]
    """
    Columns output by the final module in this tab.

    `set(columns.keys()) == set(dataframe.columns)`.
    """

    dataframe: pd.DataFrame
    """
    DataFrame output by the final module in this tab.
    """


@dataclass(frozen=True)
class QuickFix:
    """
    Suggestion from a module on how the user can improve the workflow.

    The canonical example is: "input is wrong type." What an icky error
    message! Let's add a button. "Input is wrong type. <Click to Fix>" -- much
    better.

    There's very little server-side code here: QuickFix is a client-only
    concept, so essentially our only test on the server is that it has an
    "action".

    Etymology: "Quick Fix" is a helpful Eclipse feature.
    """

    text: str
    """Text on the button"""

    action: str
    """Reducer action to invoke, such as 'prependModule'"""

    args: List
    """Action arguments, as a list"""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def coerce(cls, value: Any) -> QuickFix:
        """
        Convert any value to a QuickFix, or raise ValueError if invalid.
        """
        if isinstance(value, dict):
            try:
                # Validate this is a plain JSON object by trying to serialize
                # it. If there's a value that's meant to be List and we get
                # pd.Index, this will catch it.
                json.dumps(value)
            except TypeError as err:
                raise ValueError(str(err))
            try:
                return QuickFix(**value)
            except TypeError as err:
                raise ValueError(str(err))
        elif isinstance(value, tuple) or isinstance(value, list):
            text, action, *args = value  # raises ValueError when len too short
            try:
                # Validate this is a plain JSON object by trying to serialize
                # it. If there's a value that's meant to be List and we get
                # pd.Index, this will catch it.
                json.dumps(text)
                json.dumps(action)
                json.dumps(args)
            except TypeError as err:
                raise ValueError(str(err))
            return QuickFix(text, action, args)
        else:
            raise ValueError("Cannot build QuickFix from value: %r" % value)

    def to_arrow(self) -> atypes.QuickFix:
        assert self.action == "prependModule"
        assert len(self.args) == 2
        [module_slug, partial_params] = self.args
        return atypes.QuickFix(
            atypes.I18nMessage("TODO_i18n", [self.text]),
            atypes.QuickFixAction.PrependStep(module_slug, partial_params),
        )


def _infer_column(
    series: pd.Series, given_format: Optional[str], try_fallback: Optional[Column]
) -> Column:
    """
    Build a valid `Column` for the given Series, or raise `ValueError`.

    The logic: determine the `ColumnType` class of `series` (e.g.,
    `ColumnType.NUMBER`) and then try to initialize it with `given_format`. If
    the format is invalid, raise `ValueError` because the user tried to create
    something invalid.

    If `try_fallback` is given and of the correct `ColumnType` class, use
    `try_fallback`.

    Otherwise, construct `Column` with default format.
    """
    type_class = ColumnType.class_from_dtype(series.dtype)

    if type_class == ColumnType.NUMBER and given_format is not None:
        type = type_class(format=given_format)  # raises ValueError
    elif given_format is not None:
        raise ValueError(
            '"format" not allowed for column "%s" because it is of type "%s"'
            % (series.name, type_class().name)
        )
    elif try_fallback is not None and isinstance(try_fallback.type, type_class):
        return try_fallback
    else:
        type = type_class()

    return Column(series.name, type)


def _infer_columns(
    dataframe: pd.DataFrame,
    column_formats: Dict[str, str],
    try_fallback_columns: Iterable[Column] = [],
) -> List[Column]:
    """
    Build valid `Column`s for the given DataFrame, or raise `ValueError`.

    The logic: determine the `ColumnType` class of `series` (e.g.,
    `ColumnType.NUMBER`) and then try to initialize it with `format`. If the
    format is invalid, raise `ValueError` because the user tried to create
    something invalid.

    If no `column_format` is supplied for a column, and there's a Column in
    `try_fallback_columns` with the same name and a compatible type, use the
    `ftry_allback_columns` value.

    Otherwise, construct `Column` with default format.
    """
    try_fallback_columns = {c.name: c for c in try_fallback_columns}
    return [
        _infer_column(dataframe[c], column_formats.get(c), try_fallback_columns.get(c))
        for c in dataframe.columns
    ]


@dataclass
class ProcessResult:
    """
    Output from a module's process() method.

    A module takes a table and parameters as input, and it produces a table as
    output. Parallel to the table, it can produce an error message destined for
    the user and a JSON message destined for the module's iframe, if the module
    controls an iframe.

    All these outputs may be empty (and Workbench treats empty values
    specially).

    process() can also output column _formats_ (i.e., number formats). If
    process() doesn't format a column, `ProcessResult.coerce()` defers to
    passed "fallback" column formats so all the output columns are formatted.

    A ProcessResult object may be pickled (and passed to/from a subprocess).
    """

    dataframe: pd.DataFrame = field(default_factory=pd.DataFrame)
    """
    Data-table result.

    If it has 0 rows and 0 columns (the default), it's "zero" -- meaning future
    modules are unreachable. Usually that means `error` should be set.
    """

    error: str = ""
    """Error (if `dataframe` is zero) or warning text."""

    json: Dict[str, Any] = field(default_factory=dict)
    """Custom JSON Object to provide to iframes."""

    quick_fixes: List[QuickFix] = field(default_factory=list)
    """Quick-fix buttons to display to the user."""

    columns: List[Column] = field(default_factory=list)
    """Columns of `dataframe` (empty if `dataframe` has no columns)."""

    def _fix_columns_silently(self) -> List[Column]:
        dataframe = self.dataframe
        if list(dataframe.columns) != self.column_names:
            self.columns = _infer_columns(dataframe, {}, self.columns)

    def __post_init__(self):
        """Set self.columns attribute if needed and validate what we can."""
        self._fix_columns_silently()

    def __eq__(self, other) -> bool:
        """Fuzzy equality operator, for unit tests."""
        # self.dataframe == other.dataframe returns a dataframe. Use .equals.
        return (
            isinstance(other, ProcessResult)
            # Hack: dataframes are often not _equal_, even though they are to
            # us, because their number types may differ. This method is only
            # used in unit tests, so _really_ we should be using
            # self.assertProcessResultEquals(..., ...) instead of hacking the
            # __eq__() operator like this. But not harm done -- yet.
            and self.dataframe.astype(str).equals(other.dataframe.astype(str))
            and self.error == other.error
            and self.json == other.json
            and self.quick_fixes == other.quick_fixes
            and self.columns == other.columns
        )

    def truncate_in_place_if_too_big(self) -> "ProcessResult":
        """
        Truncate dataframe in-place and add to self.error if truncated.
        """
        # import after app startup. [2019-08-21, adamhooper] may not be needed
        from django.conf import settings

        old_len = len(self.dataframe)
        new_len = min(old_len, settings.MAX_ROWS_PER_TABLE)
        if new_len != old_len:
            self.dataframe.drop(
                range(settings.MAX_ROWS_PER_TABLE, old_len), inplace=True
            )
            warning = "Truncated output from %d rows to %d" % (old_len, new_len)
            if self.error:
                self.error = f"{self.error}\n{warning}"
            else:
                self.error = warning
            # Nix unused categories
            for column in self.dataframe:
                series = self.dataframe[column]
                if hasattr(series, "cat"):
                    series.cat.remove_unused_categories(inplace=True)

    @property
    def status(self):
        """
        Whether this data means 'ok', 'error' or 'unreachable'.

        'ok': there is a DataFrame. (If error is set, it's a warning.)
        'error': there is no DataFrame, and error is set.
        'unreachable': there is no DataFrame or error.
        """
        if self.dataframe.columns.empty:
            if self.error:
                return "error"
            else:
                return "unreachable"
        else:
            return "ok"

    @property
    def column_names(self):
        return [c.name for c in self.columns]

    @property
    def table_shape(self) -> TableShape:
        return TableShape(len(self.dataframe), self.columns)

    @classmethod
    def coerce(
        cls, value: Any, try_fallback_columns: Iterable[Column] = []
    ) -> ProcessResult:
        """
        Convert any value to a ProcessResult.

        The rules:

        * value is None => return empty dataframe
        * value is a ProcessResult => return it
        * value is a DataFrame => empty error and json
        * value is a str => error=str, empty dataframe and json
        * value is a (DataFrame, err) => empty json (either may be None)
        * value is a (DataFrame, err, dict) => obvious (any may be None)
        * value is a dict => pass it as kwargs
        * else we generate an error with empty dataframe and json

        `try_fallback_columns` is a List of Columns that should pre-empt
        automatically-generated `columns` but _not_ pre-empt
        `value['column_formats']` if it exists. For example: in a list of
        steps, we use the prior step's output columns as "fallback" definitions
        for _this_ step's output columns, if the module didn't specify others.
        This trick lets us preserve number formats implicitly -- most modules
        needn't worry about them.

        Raise `ValueError` if `value` cannot be coerced -- including if
        `validate_dataframe()` raises an error.
        """
        if value is None:
            return cls(dataframe=pd.DataFrame())
        elif isinstance(value, ProcessResult):
            # TODO ban `ProcessResult` retvals from `fetch()`, then omit this
            # case. ProcessResult should be internal.
            validate_dataframe(value.dataframe)
            return value
        elif isinstance(value, pd.DataFrame):
            validate_dataframe(value)
            columns = _infer_columns(value, {}, try_fallback_columns)
            return cls(dataframe=value, columns=columns)
        elif isinstance(value, str):
            return cls(error=value)
        elif isinstance(value, dict):
            value = dict(value)  # shallow copy
            # Coerce quick_fixes, if it's there
            try:
                value["quick_fixes"] = [
                    QuickFix.coerce(v) for v in value["quick_fixes"]
                ]
            except KeyError:
                pass

            dataframe = value.pop("dataframe", pd.DataFrame())
            validate_dataframe(dataframe)

            try:
                column_formats = value.pop("column_formats")
                value["columns"] = _infer_columns(
                    dataframe, column_formats, try_fallback_columns
                )
            except KeyError:
                pass

            try:
                return cls(dataframe=dataframe, **value)
            except TypeError as err:
                raise ValueError(
                    (
                        "ProcessResult input must only contain {dataframe, "
                        "error, json, quick_fixes, column_formats} keys"
                    )
                ) from err
        elif isinstance(value, tuple):
            if len(value) == 2:
                dataframe, error = value
                if dataframe is None:
                    dataframe = pd.DataFrame()
                if error is None:
                    error = ""
                if not isinstance(dataframe, pd.DataFrame) or not isinstance(
                    error, str
                ):
                    return cls(
                        error=(
                            (
                                "There is a bug in this module: expected "
                                "(DataFrame, str) return type, got (%s,%s)"
                            )
                            % (type(dataframe).__name__, type(error).__name__)
                        )
                    )
                validate_dataframe(dataframe)
                columns = _infer_columns(dataframe, {}, try_fallback_columns)
                return cls(dataframe=dataframe, error=error)
            elif len(value) == 3:
                dataframe, error, json = value
                if dataframe is None:
                    dataframe = pd.DataFrame()
                if error is None:
                    error = ""
                if json is None:
                    json = {}
                if (
                    not isinstance(dataframe, pd.DataFrame)
                    or not isinstance(error, str)
                    or not isinstance(json, dict)
                ):
                    return cls(
                        error=(
                            (
                                "There is a bug in this module: expected "
                                "(DataFrame, str, dict) return value, got "
                                "(%s, %s, %s)"
                            )
                            % (
                                type(dataframe).__name__,
                                type(error).__name__,
                                type(json).__name__,
                            )
                        )
                    )
                validate_dataframe(dataframe)
                columns = _infer_columns(dataframe, {}, try_fallback_columns)
                return cls(dataframe=dataframe, error=error, json=json, columns=columns)
            return cls(
                error=(
                    (
                        "There is a bug in this module: expected 2-tuple or 3-tuple "
                        "return value; got %d-tuple "
                    )
                    % len(value)
                )
            )

        return cls(
            error=(
                "There is a bug in this module: invalid return type %s"
                % type(value).__name__
            )
        )

    def to_arrow(self, path: Path) -> atypes.RenderResultOk:
        """
        Build a lower-level RenderResultOk from this ProcessResult.

        Iff this ProcessResult is not an error result, an Arrow table will be
        written to `path`, then mmapped and validated (because
        `RenderResultOk.__post_init__()` opens and validates Arrow files).

        If this ProcessResult _is_ an error result, then nothing will be
        written to `path` and the returned RenderResultOk will not refer to
        `path`.

        RenderResultOk is a lower-level (and more modern) representation of a
        module's result. Prefer it everywhere. We want to eventually deprecate
        ProcessResult.
        """
        if self.columns:
            arrow_table = pyarrow.Table.from_pandas(
                self.dataframe, preserve_index=False, nthreads=1
            )  # TODO test dictionaries stay dictionaries
            with pyarrow.RecordBatchFileWriter(str(path), arrow_table.schema) as writer:
                writer.write_table(arrow_table)
        else:
            path = None

        table = atypes.ArrowTable(path, self.table_shape.to_arrow())
        if self.error:
            error = atypes.RenderError(
                # Mark the message as English-only (deprecated)
                atypes.I18nMessage("TODO_i18n", [self.error]),
                [qf.to_arrow() for qf in self.quick_fixes],
            )
            errors = [error]
        else:
            errors = []

        return atypes.RenderResultOk(table, errors, self.json)
