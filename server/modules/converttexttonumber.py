from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
import re


def _chars_to_pattern(chars: Set[str]) -> str:
    if len(chars) == 1:
        return re.escape(next(iter(chars)))
    else:
        return '[' + ''.join([re.escape(c) for c in chars]) + ']'


NEGATIVE_CHARS = set('−-')  # One is Unicode!


class InputNumberType(Enum):
    """Option to restrict the input."""

    ANY = 'any'
    """Match something that looks like a number: integer or float."""

    INTEGER = 'int'
    """Match something that looks like an integer."""

    FLOAT = 'float'
    """Match something that looks like a number with a decimal."""

    @property
    def regex_pattern(self):
        """
        A pseudo-regex, with 'N' for neg, 'T' for thousands, 'D' for decimal.

        Later on we'll replace those placeholders with their locale-dependent
        patterns.
        """

        # Regex authorship tips:
        #
        # To match "1000" _and_ "1,000", we need to make sure the engine doesn't
        # give up on just the "1". r'\d+|\d{1,3}(,\d{3})+' will give "1" instead of
        # "1,000" because the \d+ matches _successfully_. Solution: put "\d+"
        # _after_ the match with the commas. Also, make the part with commas
        # _require_ commas. r'...(,\d{3})*' always succeeds, because it matches the
        # empty string. Use r'+' instead of r'*'.
        if self.value == 'any':
            return r'(N?(?:\d{1,3}(?:T\d{3})+|\d+)(?:D\d+)?)'
        elif self.value == 'int':
            return r'(N?(?:\d{1,3}(?:T\d{3})+|\d+))'
        else:
            return r'(N?(?:\d{1,3}(?:T\d{3})+|\d+)D\d+)'


class InputLocale(Enum):
    """Thousands separators and decimal points the user wants."""

    US = 'us'
    """United States: 1,000.00"""

    EU = 'eu'
    """Europe: 1 000,00 or 1.000,00"""

    @property
    def thousands_separator_chars(self):
        if self.value == 'us':
            return set(',_')
        else:
            return set('   ._')  # Unicode thin spaces

    @property
    def decimal_chars(self):
        if self.value == 'us':
            return set('.')
        else:
            return set(',')


@dataclass(frozen=True)
class ErrorCount:
    """
    Tally of errors in all rows.

    This stores the first erroneous value and a count of all others. It's false
    if there aren't any errors.
    """

    a_column: Optional[str] = None
    a_row: Optional[int] = None
    a_value: Optional[str] = None
    total: int = 0
    n_columns: int = 0

    def __add__(self, rhs: 'ErrorCount') -> 'ErrorCount':
        """Add more errors to this ErrorCount."""
        if not self:
            return rhs
        else:
            return replace(self, total=(self.total + rhs.total),
                           n_columns=(self.n_columns + rhs.n_columns))

    def __str__(self):
        if self.total == 1:
            n_errors_str = 'is 1 error'
        else:
            n_errors_str = f'are {self.total} errors'

        if self.n_columns == 1:
            n_columns_str = '1 column'
        else:
            n_columns_str = f'{self.n_columns} columns'

        return (
            f"'{self.a_value}' in row {self.a_row + 1} of "
            f"'{self.a_column}' cannot be converted. Overall, there "
            f"{n_errors_str} in {n_columns_str}. Select 'Convert non-numbers "
            "to null' to set these values to null."
        )

    def __len__(self):
        """
        Count errors. 0 (which means __bool__ is false) if there are none.
        """
        return self.total

    @classmethod
    def from_diff(cls, in_series: pd.Series,
                  out_series: pd.Series) -> 'ErrorCount':
        in_na = in_series.isna()
        out_na = out_series.isna()
        out_errors = out_na.index[out_na & ~in_na]

        if out_errors.empty:
            return ErrorCount()
        else:
            column = in_series.name
            row = out_errors[0]
            value = in_series[row]
            return ErrorCount(column, row, value, len(out_errors), 1)


@dataclass(frozen=True)
class Form:
    # Automatic values are for unit tests
    colnames: List[str]
    extract: bool = False
    input_number_type: InputNumberType = InputNumberType.ANY
    input_locale: InputLocale = InputLocale.US
    error_means_null: bool = False
    output_format: str = '{:,}'

    @classmethod
    def parse(cls, colnames: str, input_number_type: str,
              input_locale: str, **kwargs):
        """
        Parse user's input from kwargs.

        User input is always valid.
        """
        return cls(
            colnames=colnames.split(','),
            input_number_type=InputNumberType(input_number_type),
            input_locale=InputLocale(input_locale),
            **kwargs
        )

    @property
    def regex(self):
        """Create a regex for numbers.
        
        It may turn '[note 1]1,234.45' into '1,234.56' (depending on format).

        Configurations:

        * input_number_type:
            * 'int' may have thousands separators or may not
            * 'float' is 'int' plus required '\.\d+'
            * 'any' is 'int' plus optional '\.\d+'
        * input_locale:
            * 'us' means thousands separator is ',' (or spaces), decimal is '.'
            * 'eu' means thousands separator is '.' (or spaces), decimal is ','
        * extract: if set, use re.search; otherwise, re.fullmatch
        """
        regex_pattern = self.input_number_type.regex_pattern
        regex_str = (
            regex_pattern
            .replace(r'N', _chars_to_pattern(NEGATIVE_CHARS))
            .replace(r'D', _chars_to_pattern(self.input_locale.decimal_chars))
            .replace(
                r'T',
                _chars_to_pattern(self.input_locale.thousands_separator_chars)
            )
        )
        if not self.extract:
            regex_str = r'\A' + regex_str + r'\Z'
        return re.compile(regex_str)

    def unformat_number_text(self, series: pd.Series) -> pd.Series:
        """Remove locale-specific stuff: -1.234,56 becomes 1234.56."""
        mapping = {}
        for c in NEGATIVE_CHARS:
            if c != '-':
                mapping[ord(c)] = '-'
        for c in self.input_locale.thousands_separator_chars:
            mapping[ord(c)] = None
        for c in self.input_locale.decimal_chars:
            if c != '.':
                mapping[ord(c)] = '.'
        return series.str.translate(mapping)

    def convert_table(self, table) -> Union[pd.DataFrame, str]:
        error_count = ErrorCount()

        for colname in self.colnames:
            series = table[colname]
            if not is_numeric_dtype(series):  # it's text
                new_series, new_errors = self.convert_series(table[colname])
                table[colname] = new_series
                error_count += new_errors

        if not self.error_means_null and error_count:
            return str(error_count)

        return table

    def convert_series(self, series) -> Tuple[pd.Series, ErrorCount]:
        number_texts = series.str.extract(self.regex, expand=False)
        number_texts = self.unformat_number_text(number_texts)
        numbers = pd.to_numeric(number_texts, errors='coerce')

        return numbers, ErrorCount.from_diff(series, numbers)


# Extracts all non-negative numbers for now
def render(table, params):
    # if no column has been selected, return table
    if not params['colnames']:
        return table

    form = Form.parse(**params)
    table_or_error = form.convert_table(table)
    if isinstance(table_or_error, str):
        return table_or_error  # it's an error
    else:
        return {
            'dataframe': table_or_error,  # it's a DataFrame
            'column_formats': {c: form.output_format
                               for c in params['colnames'].split(',')}
        }


def _migrate_params_v0_to_v1(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize some names; nix 0-impute.

    * type_extract becomes input_number_type (any|int|float).
        * when extract is unchecked, force 'any' (for backwards-compat:
          in olden times, 'exact' _forced_ 'any'.)
    * type_format becomes input_locale (us|en).
    * error_means_null: new parameter; always True. (Previously, errors meant
      0 or null and were never reported. Now, errors are reported by default
      and 0 is not an option.)
    * output_format: new parameter; always {:,}.
    """

    if params['extract']:
        input_number_type = ['any', 'int', 'float'][params['type_extract']]
    else:
        input_number_type = 'any'

    return {
        'colnames': params['colnames'],
        'extract': params['extract'],
        'input_number_type': input_number_type,
        'input_locale': ['us', 'eu'][params['type_format']],
        'error_means_null': True,
        'output_format': '{:,}',
    }


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    if 'type_format' in params:
        # Params v0: had 'type_format' instead of 'input_locale'
        params = _migrate_params_v0_to_v1(params)
    return params
