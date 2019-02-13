from enum import Enum
from typing import Any, Dict, List
import numpy as np
import pandas as pd
import re

# Ignore negative numbers for now
# TODO first column goes twice


class Extract(Enum):
    """Logic to use to find a number in text."""

    ANY = 0
    """Find the first thing that looks like a number: integer or float."""

    INTEGER = 1
    """Find the first thing that looks like an integer."""

    DECIMAL = 2
    """Find the first thing that looks like a number with a decimal."""

    EXACT = 99
    """Expect the whole text value to be a number: integer or float."""


class Format(Enum):
    US = 0
    EU = 1


class Replace(Enum):
    NULL = 0
    ZERO = 1


class GentleValueError(Exception):
    pass


class Form:
    def __init__(self, colnames: List[str], type_extract: Extract,
                 type_format: Format, type_replace: Replace):
        self.colnames = colnames
        self.type_extract = type_extract
        self.type_format = type_format
        self.type_replace = type_replace

    def process(self, table):
        for colname in self.colnames:
            table[colname] = self.process_series(table[colname])

        return table

    def process_series(self, series):
        old_nulls = series.isna()

        if hasattr(series, 'cat'):
            strs = series.astype(str)
            strs[old_nulls] = np.nan
            series = strs

        if series.dtype != object:
            return series

        number_texts = extract_number_text(series, self.type_extract,
                                           self.type_format)
        number_texts = unformat_number_text(number_texts, self.type_format)
        numbers = pd.to_numeric(number_texts, errors='coerce')

        if self.type_replace == Replace.ZERO:
            numbers[numbers.isna() & ~old_nulls] = 0

        return numbers

    @classmethod
    def parse(cls, params: Dict[str, Any]) -> 'Form':
        """
        Parse user's input.

        User input is always valid.
        """
        colnames = [c for c in params['colnames'].split(',') if c]
        if params['extract']:
            type_extract = Extract(params['type_extract'])
        else:
            type_extract = Extract.EXACT
        type_format = Format(params['type_format'])
        type_replace = Replace(params['type_replace'])
        return cls(colnames, type_extract, type_format, type_replace)


# Extracts all non-negative numbers for now
def render(table, params):
    # if no column has been selected, return table
    if not params['colnames']:
        return table

    form = Form.parse(params)
    return form.process(table)


REGEXES = {
    # Regex authorship tips:
    #
    # To match "1000" _and_ "1,000", we need to make sure the engine doesn't
    # give up on just the "1". r'\d+|\d{1,3}(,\d{3})+' will give "1" instead of
    # "1,000" because the \d+ matches _successfully_. Solution: put "\d+"
    # _after_ the match with the commas. Also, make the part with commas
    # _require_ commas. r'...(,\d{3})*' always succeeds, because it matches the
    # empty string. Use r'+' instead of r'*'.
    Extract.ANY: {
        Format.US: re.compile(r'(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)'),
        Format.EU: re.compile(r'(-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?)'),
    },
    Extract.EXACT: {
        # ANY, with ^ and $
        #
        # Why the regex? Why not simply pass the number to pd.to_numeric()?
        # Because without this step, "177.1" is a valid EU number -- the
        # number 1771. That's wrong.
        Format.US: re.compile(r'^(-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)$'),
        Format.EU: re.compile(r'^(-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?)$'),
    },
    Extract.INTEGER: {
        Format.US: re.compile(r'(-?(?:\d{1,3}(?:,\d{3})+|\d+))'),
        Format.EU: re.compile(r'(-?(?:\d{1,3}(?:\.\d{3})+|\d+))'),
    },
    Extract.DECIMAL: {
        Format.US: re.compile(r'(-?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d+)'),
        Format.EU: re.compile(r'(-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d+)'),
    },
}


def extract_number_text(series: pd.Series, extract_type: Extract,
                        number_format: Format) -> pd.Series:
    """Turns '[note 1]1,234.45' into '1,234.56' (depending on format)."""
    regex = REGEXES[extract_type][number_format]
    return series.str.extract(regex, expand=False)


def unformat_number_text(series: pd.Series,
                         number_format: Format) -> pd.Series:
    """Turns '1,234.56' into '1234.56'."""
    if number_format == Format.US:
        series = series.str.translate({ord(','): None})
    else:
        series = series.str.translate({ord(','): ord('.'), ord('.'): None})

    return series
