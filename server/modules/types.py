from typing import Any, Dict
from pandas import DataFrame
from server import sanitizedataframe
from django.utils.translation import gettext as _


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
    def __init__(self, dataframe: DataFrame=None, error: str='',
                 json: Dict[str, Any]=None):
        if dataframe is None:
            dataframe = DataFrame()
        if not isinstance(dataframe, DataFrame):
            raise ValueError('dataframe must be a DataFrame')

        if not isinstance(error, str):
            raise ValueError('error must be a str')

        if json is None:
            json = {}
        if not isinstance(json, dict):
            raise ValueError('json must be a dict')

        self.dataframe = dataframe
        self.error = error
        self.json = json

    def __repr__(self) -> str:
        return (
            'ProcessResult('
            f'{repr(self.dataframe)}, '
            f'{repr(self.error)}, '
            f'{repr(self.json)}'
            ')'
        )

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
        )

    def truncate_in_place_if_too_big(self) -> 'ProcessResult':
        """Truncate dataframe in-place and add to self.error if truncated."""
        len_before = len(self.dataframe)
        if sanitizedataframe.truncate_table_if_too_big(self.dataframe):
            warning = _('Truncated output from %d rows to %d') % (len_before, len(self.dataframe))
            if self.error:
                self.error = f'{self.error}\n{warning}'
            else:
                self.error = warning

    def sanitize_in_place(self):
        """Coerce dataframe headers to strings and values to simple types."""
        sanitizedataframe.sanitize_dataframe(self.dataframe)

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
        * else we generate an error with empty dataframe and json
        """
        if value is None:
            return ProcessResult(dataframe=DataFrame())
        if isinstance(value, ProcessResult):
            return value
        if isinstance(value, DataFrame):
            return ProcessResult(dataframe=value)
        if isinstance(value, str):
            return ProcessResult(error=value)
        if isinstance(value, tuple):
            if len(value) == 2:
                dataframe, error = value
                if dataframe is None:
                    dataframe = DataFrame()
                if error is None:
                    error = ''
                if not isinstance(dataframe, DataFrame) \
                   or not isinstance(error, str):
                    return ProcessResult(error=(
                        _('There is a bug in this module: expected (DataFrame, str) return type, got (%s,%s)') %
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
                        _('There is a bug in this module: expected (DataFrame, str, dict) return value, got (%s, %s, %s)') %
                        ( type(dataframe).__name__, type(error).__name__, type(json).__name__)
                    ))
                return ProcessResult(dataframe=dataframe, error=error,
                                     json=json)
            return ProcessResult(error=(
                _('There is a bug in this module: expected 2-tuple or 3-tuple return value; got %d-tuple ') % len(value)
            ))

        return ProcessResult(
            error=_('There is a bug in this module: invalid return type %s') % type(value).__name__
        )
