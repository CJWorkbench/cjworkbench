from collections import namedtuple
from typing import Any, Dict, List
from pandas import DataFrame
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from server import sanitizedataframe
from django.utils.translation import gettext as _


Column = namedtuple('Column', ['name', 'type'])


def _dtype_to_column_type(dtype) -> str:
    """Return 'text', 'number' or 'datetime'."""
    if is_numeric_dtype(dtype):
        return 'number'
    elif is_datetime64_dtype(dtype):
        return 'datetime'
    elif dtype == object or dtype == 'category':
        return 'text'
    else:
        raise ValueError(f'Unknown dtype: {dtype}')


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
                    'QuickFix needs "text", "action" and "args" keys: {value}'
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
    def __init__(self, dataframe: DataFrame=None, error: str='', *,
                 json: Dict[str, Any]={}, quick_fixes: List[QuickFix]=[]):
        if dataframe is None:
            dataframe = DataFrame()
        if not isinstance(dataframe, DataFrame):
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
            warning = (_('Truncated output from %d rows to %d')
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
        if self.dataframe.empty:
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
        return [_dtype_to_column_type(t) for t in self.dataframe.dtypes]

    @property
    def columns(self):
        return [Column(c, t)
                for c, t in zip(self.column_names, self.column_types)]

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
            return ProcessResult(dataframe=DataFrame())
        elif isinstance(value, ProcessResult):
            return value
        elif isinstance(value, DataFrame):
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
                    dataframe = DataFrame()
                if error is None:
                    error = ''
                if not isinstance(dataframe, DataFrame) \
                   or not isinstance(error, str):
                    return ProcessResult(error=(
                        _('There is a bug in this module: expected '
                          '(DataFrame, str) return type, got (%s,%s)') %
                        (type(dataframe).__name__, type(error).__name__)
                    ))
                return ProcessResult(dataframe=dataframe, error=error)
            elif len(value) == 3:
                dataframe, error, json = value
                if dataframe is None:
                    dataframe = DataFrame()
                if error is None:
                    error = ''
                if json is None:
                    json = {}
                if not isinstance(dataframe, DataFrame) \
                   or not isinstance(error, str) \
                   or not isinstance(json, dict):
                    return ProcessResult(error=(
                        _('There is a bug in this module: expected '
                          '(DataFrame, str, dict) return value, got '
                          '(%s, %s, %s)') %
                        (type(dataframe).__name__, type(error).__name__,
                         type(json).__name__)
                    ))
                return ProcessResult(dataframe=dataframe, error=error,
                                     json=json)
            return ProcessResult(error=(
                _('There is a bug in this module: expected 2-tuple or 3-tuple '
                  'return value; got %d-tuple ') % len(value)
            ))

        return ProcessResult(
            error=(_('There is a bug in this module: invalid return type %s')
                   % type(value).__name__)
        )
