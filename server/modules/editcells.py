from itertools import groupby
import logging
from typing import Any, Dict, List, Union
import pandas as pd
from pandas.api.types import is_numeric_dtype
import numpy as np
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import parse_json_param

logger = logging.getLogger(__name__)


class Edit:
    def __init__(self, *, row, col, value):
        self.row = int(row)
        self.col = str(col)
        self.value = str(value)


def apply_edits(series: pd.Series, edits: List[Edit]) -> pd.Series:
    """
    Change a single cell value, with correct type handling.

    If the (str) edit value can be converted to numeric and the cell is
    numeric, edit without casting (or cast from int64 to float64 if necessary).
    If the column is numeric and the edit value is str, convert the column to
    str.
    """
    keys = [edit.row for edit in edits]
    str_values = pd.Series([edit.value for edit in edits], dtype=str)

    if is_numeric_dtype(series):
        try:
            num_values = pd.to_numeric(str_values)
            # pandas will upcast int64 col to float64 if needed
            series[keys] = num_values
            return series
        except ValueError:
            # convert numbers to string, replacing NaN with ''
            pass  # don't return: we'll handle this in the default case below

    if hasattr(series, 'cat'):
        series.cat.add_categories(set(str_values) - set(series.cat.categories),
                                  inplace=True)
        series[keys] = str_values
        return series

    t = series
    series = t.astype(str)
    series[t.isna()] = np.nan
    series[keys] = str_values

    return series


def parse_json(edits_arr: List[Dict[str, Any]]) -> Union[List[Edit], str]:
    """Parse a list of Edits from a str, or return an error string."""
    if not edits_arr:  # "empty JSON" is {}, which matches
        return []

    if not isinstance(edits_arr, list):
        return 'Internal error: invalid JSON: not an Array'

    try:
        edits = [Edit(**item) for item in edits_arr]
    except TypeError:
        return (
            'Internal error: invalid JSON: '
            'Objects must all have row, col and value'
        )
    except ValueError:
        return 'Internal error: invalid JSON: "row" must be a Number'

    return edits


class EditCells(ModuleImpl):
    # Execute our edits. Stored in parameter as a json serialized array that
    # looks like this:
    #  [
    #    { 'row': 3, 'col': 'foo', 'value':'bar' },
    #    { 'row': 6, 'col': 'food', 'value':'sandwich' },
    #    ...
    #  ]
    @staticmethod
    def render(table, params, **kwargs):
        edits = parse_json(parse_json_param(params['celledits']))
        if isinstance(edits, str):
            # [adamhooper, 2019-01-31] Huh? How does this happen?
            return ProcessResult(error=edits)

        # Ignore missing columns and rows: delete them from the Array of edits
        edits = [edit for edit in edits
                 if edit.col in table.columns
                 and edit.row >= 0 and edit.row < len(table)]

        for column, column_edits in groupby(edits, lambda e: e.col):
            series = table[column]
            series2 = apply_edits(series, list(column_edits))
            if series2 is not series:
                table[column] = series2

        return table
