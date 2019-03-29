from __future__ import annotations

from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from string import Formatter
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from server import sanitizedataframe  # TODO nix this dependency


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
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the type: 'text', 'number' or 'datetime'.
        """
        pass

    @classmethod
    def from_dtype(cls, dtype) -> ColumnType:
        """
        Determine ColumnType based on pandas/numpy `dtype`.

        If the type is Number or Datetime, it will have an "empty"
        (auto-generated) format.
        """
        if is_numeric_dtype(dtype):
            return ColumnType.NUMBER()
        elif is_datetime64_dtype(dtype):
            return ColumnType.DATETIME()
        elif dtype == object or dtype == 'category':
            return ColumnType.TEXT()
        else:
            raise ValueError(f'Unknown dtype: {dtype}')


@dataclass(frozen=True)
class ColumnTypeText(ColumnType):
    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        return series

    # override
    @property
    def name(self) -> str:
        return 'text'


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

    _IntTypeSpecifiers = set('bcdoxXn')
    """
    Type names that operate on integer (as opposed to float).

    Python `format()` auto-converts int to float, but it doesn't auto-convert
    float to int. Workbench does auto-convert float to int: any format that
    works for one Number must work for all Numbers.
    """

    def __init__(self, format_s: str):
        # parts: a list of (literal_text, field_name, format_spec, conversion)
        #
        # The "literal_text" always comes _before_ the field. So we end up
        # with three possibilities:
        #
        #    "prefix{}suffix": [(prefix, "", "", ""), (suffix, None...)]
        #    "prefix{}": [(prefix, "", "", '")]
        #    "{}suffix": [("", "", "", ""), (suffix, None...)]
        parts = list(Formatter().parse(format_s))

        if (
            len(parts) > 2
            or len(parts) == 2 and parts[1][1] is not None
        ):
            raise ValueError('Can only format one number')

        if parts[0][1] != '':
            raise ValueError('Field names or numbers are not allowed')

        if parts[0][3] is not None:
            raise ValueError('Field converters are not allowed')

        self._prefix = parts[0][0]
        self._format_spec = parts[0][2]
        if len(parts) == 2:
            self._suffix = parts[1][0]
        else:
            self._suffix = ''
        self._need_int = (
            self._format_spec
            and self._format_spec[-1] in self._IntTypeSpecifiers
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
        return self._prefix + format(value, self._format_spec) + self._suffix


@dataclass(frozen=True)
class ColumnTypeNumber(ColumnType):
    # https://docs.python.org/3/library/string.html#format-specification-mini-language
    format: str = '{}'  # Python format() string
    # TODO handle locale, too: format depends on it. Python will make this
    # difficult because it can't format a string in an arbitrary locale: it can
    # only do it using global variables, which we can't use.

    def __post_init__(self):
        formatter = NumberFormatter(self.format)  # raises ValueError
        object.__setattr__(self, '_formatter', formatter)

    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        return series.map(self._formatter.format, na_action='ignore')

    # override
    @property
    def name(self) -> str:
        return 'number'


@dataclass(frozen=True)
class ColumnTypeDatetime(ColumnType):
    # # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    # format: str = '{}'  # Python format() string

    # # TODO handle locale, too: format depends on it. Python will make this
    # # difficult because it can't format a string in an arbitrary locale: it can
    # # only do it using global variables, which we can't use.

    # override
    def format_series(self, series: pd.Series) -> pd.Series:
        return series.dt.strftime('%FT%T.%fZ').replace('NaT', np.nan)

    # override
    @property
    def name(self) -> str:
        return 'datetime'


# Aliases to help with import. e.g.:
# from cjworkbench.types import Column, ColumnType
# column = Column('A', ColumnType.NUMBER('{:,.2f}'))
ColumnType.TEXT = ColumnTypeText
ColumnType.NUMBER = ColumnTypeNumber
ColumnType.DATETIME = ColumnTypeDatetime

ColumnType.TypeLookup = {
    'text': ColumnType.TEXT,
    'number': ColumnType.NUMBER,
    'datetime': ColumnType.DATETIME,
}


@dataclass(frozen=True)
class Column:
    """
    A column definition.
    """

    name: str  # Name of the column
    type: ColumnType  # How it's displayed

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type.name,
            **asdict(self.type),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> Column:
        return cls.from_kwargs(**d)

    @classmethod
    def from_kwargs(cls, name: str, type: str, **column_type_kwargs) -> ColumnType:
        type_cls = ColumnType.TypeLookup[type]
        return Column(name, type_cls(**column_type_kwargs))


class TableShape:
    """
    The rows and columns of a table -- devoid of data.
    """
    def __init__(self, nrows: int, columns: List[Column]):
        self.nrows = nrows
        self.columns = columns

    def __repr__(self):
        return 'TableShape' + repr((self.nrows, self.columns))

    def __eq__(self, rhs):
        return (
            isinstance(rhs, TableShape)
            and (self.nrows, self.columns) == (rhs.nrows, rhs.columns)
        )


class StepResultShape:
    """
    Low-RAM metadata about a ProcessResult.
    """

    def __init__(self, status: str, table_shape: TableShape):
        self.status = status
        self.table_shape = table_shape


RenderColumn = namedtuple('RenderColumn', ('name', 'type', 'format'))
"""
Column presented to a render() function in its `input_columns` argument.

A column has a `name` and a `type`. The `type` is one of "number", "text" or
"datetime".
"""

TabOutput = namedtuple('TabOutput', ('slug', 'name', 'columns', 'dataframe'))
"""
Tab data presented to a render() function.

A tab has `slug` (JS-side ID), `name` (user-assigned tab name), `dataframe`
(pandas.DataFrame), and `columns` (dict of `RenderColumn`, keyed by each column
in `dataframe.columns`.)

The `columns` is designed to mirror the `input_columns` argument to render().
It's a Dict[str, RenderColumn].
"""


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
    def __init__(self, text, action, args):
        self.text = text
        self.action = action
        self.args = args

    @staticmethod
    def coerce(value):
        """Convert tuple/dict to QuickFix."""
        if isinstance(value, QuickFix):
            return value
        elif isinstance(value, tuple):
            if len(value) < 2:
                raise ValueError(f'QuickFix must have (action,text)')
            else:
                return QuickFix(value[0], value[1], list(value[2:]))
        elif isinstance(value, dict):
            try:
                return QuickFix(value['text'], value['action'], value['args'])
            except KeyError:
                raise ValueError(
                    f'QuickFix needs "text", "action" and "args" keys: {value}'
                )
        else:
            raise ValueError(f'QuickFix is not a tuple or dict: {value}')

    def to_dict(self):
        return {
            'text': self.text,
            'action': self.action,
            'args': self.args,
        }

    def __eq__(self, other) -> bool:
        """Fuzzy equality operator, for unit tests."""
        return (
            isinstance(other, QuickFix)
            and self.text == other.text
            and self.action == other.action
            and self.args == other.args
        )

    def __repr__(self) -> str:
        tup = (self.text, self.action, self.args)
        return 'QuickFix' + repr(tup)


class ProcessResult:
    """
    Output from a module's process() method.

    A module takes a table and parameters as input, and it produces a table as
    output. Parallel to the table, it can produce an error message destined for
    the user and a JSON message destined for the module's iframe, if the module
    controls an iframe.

    All these outputs may be empty (and Workbench treats empty values
    specially).

    A ProcessResult object may be pickled.
    """
    def __init__(self, dataframe: pd.DataFrame = None, error: str = '', *,
                 json: Dict[str, Any] = {}, quick_fixes: List[QuickFix] = []):
        if dataframe is None:
            dataframe = pd.DataFrame()
        if not isinstance(dataframe, pd.DataFrame):
            raise ValueError('dataframe must be a DataFrame')

        if not isinstance(error, str):
            raise ValueError('error must be a str')

        if not isinstance(json, dict):
            raise ValueError('json must be a dict')

        if not isinstance(quick_fixes, list):
            raise ValueError('quick_fixes must be a list')

        self.dataframe = dataframe
        self.error = error
        self.json = json
        self.quick_fixes = quick_fixes

    def __repr__(self) -> str:
        return 'ProcessResult' + repr((self.dataframe, self.error, self.json,
                                       self.quick_fixes))

    def __eq__(self, other) -> bool:
        """Fuzzy equality operator, for unit tests."""
        # self.dataframe == other.dataframe returns a dataframe. Use .equals.
        return (
            isinstance(other, ProcessResult)
            and self.dataframe.astype(str).equals(
                other.dataframe.astype(str)
            )
            and self.error == other.error
            and self.json == other.json
            and self.quick_fixes == other.quick_fixes
        )

    def truncate_in_place_if_too_big(self) -> 'ProcessResult':
        """Truncate dataframe in-place and add to self.error if truncated."""
        len_before = len(self.dataframe)
        if sanitizedataframe.truncate_table_if_too_big(self.dataframe):
            warning = ('Truncated output from %d rows to %d'
                       % (len_before, len(self.dataframe)))
            if self.error:
                self.error = f'{self.error}\n{warning}'
            else:
                self.error = warning

    def sanitize_in_place(self):
        """Coerce dataframe headers to strings and values to simple types."""
        sanitizedataframe.sanitize_dataframe(self.dataframe)

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
                return 'error'
            else:
                return 'unreachable'
        else:
            return 'ok'

    @property
    def column_names(self):
        return list(self.dataframe.columns)

    @property
    def column_types(self):
        return [ColumnType.from_dtype(t) for t in self.dataframe.dtypes]

    @property
    def columns(self):
        return [Column(c, t)
                for c, t in zip(self.column_names, self.column_types)]

    @property
    def table_shape(self) -> TableShape:
        return TableShape(len(self.dataframe), self.columns)

    @staticmethod
    def coerce(value: Any) -> 'ProcessResult':
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
        """
        if value is None:
            return ProcessResult(dataframe=pd.DataFrame())
        elif isinstance(value, ProcessResult):
            return value
        elif isinstance(value, pd.DataFrame):
            return ProcessResult(dataframe=value)
        elif isinstance(value, str):
            return ProcessResult(error=value)
        elif isinstance(value, dict):
            value = dict(value)  # shallow copy
            # Coerce quick_fixes, if it's there
            try:
                value['quick_fixes'] = [QuickFix.coerce(v)
                                        for v in value['quick_fixes']]
            except KeyError:
                pass

            try:
                return ProcessResult(**value)
            except TypeError as err:
                raise ValueError(
                    ('ProcessResult input must only contain '
                     '{dataframe, error, json, quick_fixes} keys'),
                ) from err
        elif isinstance(value, tuple):
            if len(value) == 2:
                dataframe, error = value
                if dataframe is None:
                    dataframe = pd.DataFrame()
                if error is None:
                    error = ''
                if not isinstance(dataframe, pd.DataFrame) \
                   or not isinstance(error, str):
                    return ProcessResult(error=(
                        ('There is a bug in this module: expected '
                         '(DataFrame, str) return type, got (%s,%s)') %
                        (type(dataframe).__name__, type(error).__name__)
                    ))
                return ProcessResult(dataframe=dataframe, error=error)
            elif len(value) == 3:
                dataframe, error, json = value
                if dataframe is None:
                    dataframe = pd.DataFrame()
                if error is None:
                    error = ''
                if json is None:
                    json = {}
                if not isinstance(dataframe, pd.DataFrame) \
                   or not isinstance(error, str) \
                   or not isinstance(json, dict):
                    return ProcessResult(error=(
                        ('There is a bug in this module: expected '
                         '(DataFrame, str, dict) return value, got '
                         '(%s, %s, %s)') %
                        (type(dataframe).__name__, type(error).__name__,
                         type(json).__name__)
                    ))
                return ProcessResult(dataframe=dataframe, error=error,
                                     json=json)
            return ProcessResult(error=(
                ('There is a bug in this module: expected 2-tuple or 3-tuple '
                 'return value; got %d-tuple ') % len(value)
            ))

        return ProcessResult(
            error=('There is a bug in this module: invalid return type %s'
                   % type(value).__name__)
        )
