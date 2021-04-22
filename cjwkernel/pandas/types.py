# LEGACY types. TODO migrate most of these to cjwkernel.types.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, NamedTuple, Optional

import numpy as np
import pandas as pd
import pyarrow as pa
from pandas.api.types import is_datetime64_dtype, is_numeric_dtype

from cjwmodule.i18n import I18nMessage
from cjwmodule.arrow.format import parse_number_format
from cjwpandasmodule.validate import validate_dataframe

from .. import settings
from .. import types as atypes
from . import moduletypes as mtypes
from ..i18n import TODO_i18n, trans

ColumnType = atypes.ColumnType
Column = atypes.Column
QuickFix = atypes.QuickFix
QuickFixAction = atypes.QuickFixAction
RenderError = atypes.RenderError


class RenderColumn(NamedTuple):
    """Column presented to a render() function in its `input_columns` argument.

    A column has a `name` and a `type`. The `type` is one of "date", "number",
    "text" or "timestamp".
    """

    name: str
    """Column name in the DataFrame."""

    type: Literal["date", "number", "text", "timestamp"]
    """Column type."""

    format: Optional[str]
    """Format string (for 'number') or date unit (for 'date').

    >>> column = RenderColumn('A', 'number', '{:,d} bottles of beer')
    >>> column.format.format(1234)
    '1,234 bottles of beer'
    """


class TabOutput(NamedTuple):
    """Tab data presented to a render() function.

    A tab has `name` (user-assigned tab name), `dataframe` (pandas.DataFrame)
    and `columns` (dict of `RenderColumn`, keyed by each column in
    `dataframe.columns`.)

    `columns` is designed to mirror the `input_columns` argument to render().
    """

    name: str
    """Tab name visible to the user and editable by the user."""

    columns: Dict[str, RenderColumn]
    """Columns output by the final module in this tab.

    `set(columns.keys()) == set(dataframe.columns)`.
    """

    dataframe: pd.DataFrame
    """DataFrame output by the final module in this tab."""


def coerce_I18nMessage(value: mtypes.Message) -> I18nMessage:
    if isinstance(value, str):
        return TODO_i18n(value)
    elif isinstance(value, tuple):
        if len(value) < 2 or len(value) > 3:
            raise ValueError("This tuple cannot be coerced to I18nMessage: %s" % value)
        if not isinstance(value[0], str):
            raise ValueError(
                "Message ID must be string, got %s" % type(value[0]).__name__
            )
        if not isinstance(value[1], dict):
            raise ValueError(
                "Message arguments must be a dict, got %s" % type(value[1]).__name__
            )
        if len(value) == 3:
            source = value[2]
            if source not in ["module", "cjwmodule", "cjwparse", None]:
                raise ValueError("Invalid i18n message source %r" % source)
        else:
            source = None
        return I18nMessage(value[0], value[1], source)
    else:
        raise ValueError(
            "%s is of type %s, which cannot be coerced to I18nMessage"
            % (value, type(value).__name__)
        )


def coerce_QuickFixAction(action: str, args: List) -> QuickFixAction:
    if action != "prependModule":
        raise ValueError("action must be prependModule")
    if len(args) != 2:
        raise ValueError("args must be [module_slug, partial_params]")
    [module_slug, partial_params] = args
    if not isinstance(module_slug, str):
        raise ValueError("args[module_slug] must be str")
    if not isinstance(partial_params, dict):
        raise ValueError("args[partial_params] must be dict")
    return QuickFixAction.PrependStep(module_slug, partial_params)


def coerce_QuickFix(value):
    if isinstance(value, dict):
        try:
            # Validate this is a plain JSON object by trying to serialize
            # it. If there's a value that's meant to be List and we get
            # pd.Index, this will catch it.
            json.dumps(value)
        except TypeError as err:
            raise ValueError(str(err))

        kwargs = dict(value)  # shallow copy
        try:
            raw_text = kwargs.pop("text")
        except KeyError:
            raise ValueError("Missing text from quick fix")
        text = coerce_I18nMessage(raw_text)

        try:
            action = coerce_QuickFixAction(**kwargs)
        except TypeError as err:
            raise ValueError(str(err))
        return QuickFix(text, action)
    else:
        raise ValueError("Cannot build QuickFix from value: %r" % value)


def _infer_column(
    series: pd.Series, given_format: Optional[str], try_fallback: Optional[Column]
) -> Column:
    """
    Build a valid `Column` for the given Series, or raise `ValueError`.

    The logic: determine the `ColumnType` class of `series` (e.g.,
    `ColumnType.Number`) and then try to initialize it with `given_format`. If
    the format is invalid, raise `ValueError` because the user tried to create
    something invalid.

    If `try_fallback` is given and of the correct `ColumnType` class, use
    `try_fallback`.

    Otherwise, construct `Column` with default format.
    """
    # Determine ColumnType class, based on pandas/numpy `dtype`.
    dtype = series.dtype
    if is_numeric_dtype(dtype):
        if given_format is not None:
            parse_number_format(given_format)
            return Column(series.name, ColumnType.Number(format=given_format))
        elif try_fallback is not None and isinstance(
            try_fallback.type, ColumnType.Number
        ):
            return try_fallback
        else:
            return Column(series.name, ColumnType.Number(format="{:,}"))
    elif is_datetime64_dtype(dtype):
        if given_format is not None:
            raise ValueError(
                '"format" not allowed for column "%s" because it is of type "timestamp"'
                % (series.name,)
            )
        return Column(series.name, ColumnType.Timestamp())
    elif pd.PeriodDtype(freq="D") == dtype:
        if given_format is not None:
            if given_format not in {"day", "week", "month", "quarter", "year"}:
                raise ValueError(
                    'Unit must be "day", "week", "month", "quarter" or "year"; got %r for column "%s"'
                    % (given_format, series.name)
                )
            return Column(series.name, ColumnType.Date(unit=given_format))
        elif try_fallback is not None and isinstance(
            try_fallback.type, ColumnType.Date
        ):
            return try_fallback
        else:
            return Column(series.name, ColumnType.Date(unit="day"))
    elif dtype == object or dtype == "category":
        if given_format is not None:
            raise ValueError(
                '"format" not allowed for column "%s" because it is of type "text"'
                % (series.name,)
            )
        return Column(series.name, ColumnType.Text())
    else:
        raise ValueError(f"Unknown dtype: {dtype}")


def _infer_columns(
    dataframe: pd.DataFrame,
    column_formats: Dict[str, str],
    try_fallback_columns: Iterable[Column] = [],
) -> List[Column]:
    """
    Build valid `Column`s for the given DataFrame, or raise `ValueError`.

    The logic: determine the `ColumnType` class of `series` (e.g.,
    `ColumnType.Number`) and then try to initialize it with `format`. If the
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


def _dtype_to_arrow_type(dtype: np.dtype) -> pa.DataType:
    if dtype == np.int8:
        return pa.int8()
    elif dtype == np.int16:
        return pa.int16()
    elif dtype == np.int32:
        return pa.int32()
    elif dtype == np.int64:
        return pa.int64()
    elif dtype == np.uint8:
        return pa.uint8()
    elif dtype == np.uint16:
        return pa.uint16()
    elif dtype == np.uint32:
        return pa.uint32()
    elif dtype == np.uint64:
        return pa.uint64()
    elif dtype == np.float16:
        return pa.float16()
    elif dtype == np.float32:
        return pa.float32()
    elif dtype == np.float64:
        return pa.float64()
    elif dtype.kind == "M":
        # [2019-09-17] Pandas only allows "ns" unit -- as in, datetime64[ns]
        # https://github.com/pandas-dev/pandas/issues/7307#issuecomment-224180563
        assert dtype.str.endswith("[ns]")
        return pa.timestamp(unit="ns", tz=None)
    elif dtype == np.object_:
        return pa.string()
    else:
        raise RuntimeError("Unhandled dtype %r" % dtype)


def series_to_arrow_array(series: pd.Series) -> pa.Array:
    """
    Convert a Pandas series to an in-memory Arrow array.
    """
    if hasattr(series, "cat"):
        return pa.DictionaryArray.from_arrays(
            # Pandas categorical value "-1" means None
            pa.Array.from_pandas(series.cat.codes, mask=(series.cat.codes == -1)),
            series_to_arrow_array(series.cat.categories),
        )
    elif pd.PeriodDtype(freq="D") == series.dtype:
        return pa.array(
            [(None if v is pd.NaT else v.ordinal) for v in series], type=pa.date32()
        )
    else:
        return pa.array(series, type=_dtype_to_arrow_type(series.dtype))


def _fix_arrow_field(field: pa.Field, column_type: ColumnType):
    if isinstance(column_type, ColumnType.Date):
        return field.with_metadata({"unit": column_type.unit})
    if isinstance(column_type, ColumnType.Number):
        return field.with_metadata({"format": column_type.format})
    return field


def dataframe_to_arrow_table(
    dataframe: pd.DataFrame, columns: List[Column], path: Path
) -> None:
    """Write `dataframe` to an Arrow file."""
    arrays = []
    for column in columns:
        arrays.append(series_to_arrow_array(dataframe[column.name]))

    arrow_table_without_metadata = pa.Table.from_arrays(
        arrays, names=[c.name for c in columns]
    )
    fields = [
        _fix_arrow_field(arrow_table_without_metadata.schema.field(i), columns[i].type)
        for i in range(len(columns))
    ]
    arrow_table = pa.table(arrow_table_without_metadata.columns, pa.schema(fields))

    with pa.RecordBatchFileWriter(str(path), arrow_table.schema) as writer:
        writer.write_table(arrow_table)


def _arrow_field_to_render_column(field: pa.Field) -> RenderColumn:
    if pa.types.is_integer(field.type) or pa.types.is_floating(field.type):
        return RenderColumn(
            field.name, "number", field.metadata[b"format"].decode("utf-8")
        )
    elif pa.types.is_date32(field.type):
        return RenderColumn(field.name, "date", field.metadata[b"unit"].decode("utf-8"))
    elif pa.types.is_timestamp(field.type):
        return RenderColumn(field.name, "timestamp", None)
    else:
        return RenderColumn(field.name, "text", None)


def arrow_schema_to_render_columns(schema: pa.Schema) -> Dict[str, RenderColumn]:
    return {
        name: _arrow_field_to_render_column(schema.field(i))
        for i, name in enumerate(schema.names)
    }


def coerce_RenderError(value: mtypes.RenderError) -> RenderError:
    if not value:
        raise ValueError("Error cannot be empty")
    elif isinstance(value, (str, tuple)):
        return RenderError(coerce_I18nMessage(value))
    elif isinstance(value, dict):
        try:
            message = coerce_I18nMessage(value["message"])
        except KeyError:
            raise ValueError("Missing 'message' in %s" % value)

        quick_fixes = [coerce_QuickFix(qf) for qf in value.get("quickFixes", [])]

        return RenderError(message, quick_fixes)
    else:
        raise ValueError(
            "Values of type %s cannot be coerced to module errors"
            % type(value).__name__
        )


def coerce_RenderError_list(
    error_or_errors: Optional[mtypes.RenderErrors],
) -> List[RenderError]:
    if error_or_errors is None or (
        isinstance(error_or_errors, str) and not error_or_errors
    ):
        return []
    elif isinstance(error_or_errors, list):
        return [coerce_RenderError(error) for error in error_or_errors]
    else:
        return [coerce_RenderError(error_or_errors)]


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

    errors: List[RenderError] = field(default_factory=list)
    """Errors (if `dataframe` is zero) or warning texts, as `I18nMessage`s; 
    each one may be accompanied by a list of quick fixes."""

    json: Dict[str, Any] = field(default_factory=dict)
    """Custom JSON Object to provide to iframes."""

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
            and self.errors == other.errors
            and self.json == other.json
            and self.columns == other.columns
        )

    def truncate_in_place_if_too_big(self) -> "ProcessResult":
        """
        Truncate dataframe in-place and add to self.errors if truncated.
        """
        old_len = len(self.dataframe)
        new_len = min(old_len, settings.MAX_ROWS_PER_TABLE)
        if new_len != old_len:
            self.dataframe.drop(
                range(settings.MAX_ROWS_PER_TABLE, old_len), inplace=True
            )
            self.errors.append(
                RenderError(
                    trans(
                        "py.cjwkernel.pandas.types.ProcessResult.truncate_in_place_if_too_big.warning",
                        default="Truncated output from {old_number} rows to {new_number}",
                        arguments={"old_number": old_len, "new_number": new_len},
                    )
                )
            )
            self.dataframe.reset_index(inplace=True, drop=True)
            # Nix unused categories
            for column in self.dataframe:
                series = self.dataframe[column]
                if hasattr(series, "cat"):
                    series.cat.remove_unused_categories(inplace=True)

    @property
    def column_names(self):
        return [c.name for c in self.columns]

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
        * value is a ModuleError => errors get populated using the data in it; empty dataframe and json
        * value is a (DataFrame, ModuleError) => empty json (either may be None)
        * value is a (DataFrame, ModuleError, dict) => obvious (any may be None)
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
            validate_dataframe(value.dataframe, settings=settings)
            return value
        elif isinstance(value, list) or isinstance(value, str):
            return cls(errors=coerce_RenderError_list(value))
        elif isinstance(value, pd.DataFrame):
            validate_dataframe(value, settings=settings)
            columns = _infer_columns(value, {}, try_fallback_columns)
            return cls(dataframe=value, columns=columns)
        elif isinstance(value, dict):
            return cls._coerce_dict(value, try_fallback_columns)
        elif isinstance(value, tuple):
            if len(value) == 2:
                return cls._coerce_2tuple(value, try_fallback_columns)
            elif len(value) == 3:
                return cls._coerce_3tuple(value, try_fallback_columns)
            else:
                raise ValueError(
                    "Expected 2-tuple or 3-tuple return value; got %d-tuple"
                    % len(value)
                )
        else:
            raise ValueError("Invalid return type %s" % type(value).__name__)

    @classmethod
    def _coerce_2tuple(
        cls, value, try_fallback_columns: Iterable[Column] = []
    ) -> ProcessResult:
        if isinstance(value[0], str) and isinstance(value[1], dict):
            return cls(errors=[coerce_RenderError(value)])
        elif isinstance(value[0], pd.DataFrame) or value[0] is None:
            dataframe, error = value
            if dataframe is None:
                dataframe = pd.DataFrame()

            errors = coerce_RenderError_list(error)

            validate_dataframe(dataframe, settings=settings)
            columns = _infer_columns(dataframe, {}, try_fallback_columns)
            return cls(dataframe=dataframe, errors=errors, columns=columns)
        else:
            raise ValueError(
                "Expected (Dataframe, RenderError) or (str, dict) return type; got (%s,%s)"
                % (type(value[0]).__name__, type(value[1]).__name__)
            )

    @classmethod
    def _coerce_3tuple(
        cls, value, try_fallback_columns: Iterable[Column] = []
    ) -> ProcessResult:
        if isinstance(value[0], str) and isinstance(value[1], dict):
            return cls(errors=[coerce_RenderError(value)])
        elif isinstance(value[0], pd.DataFrame) or value[0] is None:
            dataframe, error, json = value
            if dataframe is None:
                dataframe = pd.DataFrame()
            elif not isinstance(dataframe, pd.DataFrame):
                raise ValueError("Expected DataFrame got %s" % type(dataframe).__name__)
            if json is None:
                json = {}
            elif not isinstance(json, dict):
                raise ValueError("Expected JSON dict, got %s" % type(json).__name__)

            errors = coerce_RenderError_list(error)

            validate_dataframe(dataframe, settings=settings)
            columns = _infer_columns(dataframe, {}, try_fallback_columns)
            return cls(dataframe=dataframe, errors=errors, json=json, columns=columns)
        else:
            raise ValueError(
                "Expected (Dataframe, RenderError, json) or I18nMessage return type; got (%s,%s, %s)"
                % (
                    type(value[0]).__name__,
                    type(value[1]).__name__,
                    type(value[2]).__name__,
                )
            )

    @classmethod
    def _coerce_dict(
        cls, value, try_fallback_columns: Iterable[Column] = []
    ) -> ProcessResult:
        if "message" in value and "quickFixes" in value:
            return cls(errors=[coerce_RenderError(value)])
        else:
            value = dict(value)  # shallow copy
            errors = coerce_RenderError_list(value.pop("errors", []))

            # Coerce old-style error and quick_fixes, if it's there
            if "error" in value:
                legacy_error_message = coerce_I18nMessage(value.pop("error"))
                legacy_error_quick_fixes = [
                    coerce_QuickFix(v) for v in value.pop("quick_fixes", [])
                ]
                errors.append(
                    RenderError(legacy_error_message, legacy_error_quick_fixes)
                )
            elif "quick_fixes" in value:
                raise ValueError("You cannot return quick fixes without an error")

            dataframe = value.pop("dataframe", pd.DataFrame())
            validate_dataframe(dataframe, settings=settings)

            column_formats = value.pop("column_formats", {})
            value["columns"] = _infer_columns(
                dataframe, column_formats, try_fallback_columns
            )

            try:
                return cls(dataframe=dataframe, errors=errors, **value)
            except TypeError as err:
                raise ValueError(
                    (
                        "ProcessResult input must only contain {dataframe, "
                        "errors, json, column_formats} keys"
                    )
                ) from err

    def to_arrow(self, path: Path) -> atypes.RenderResult:
        """Build a lower-level RenderResult from this ProcessResult.

        An Arrow table (maybe-empty) will be written to `path`.

        RenderResult is a lower-level (and more modern) representation of a
        module's result. Prefer it everywhere. We will deprecate ProcessResult.
        """
        dataframe_to_arrow_table(self.dataframe, self.columns, path)
        return atypes.RenderResult(errors=self.errors, json=self.json)
