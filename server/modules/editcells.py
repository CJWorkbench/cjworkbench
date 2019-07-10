from dataclasses import dataclass
from itertools import groupby
import json
import logging
from typing import List
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

logger = logging.getLogger(__name__)


@dataclass
class Edit:
    row: int
    col: str
    value: str


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

    if hasattr(series, "cat"):
        str_values_set = set(str_values)
        old_values_set = set(series.cat.categories)
        if str_values_set != old_values_set:
            # Create new series. Otherwise for some reason the table's dtypes
            # don't pick up on category changes.
            series = series.cat.add_categories(str_values_set - old_values_set)
            series[keys] = str_values
            series.cat.remove_unused_categories(inplace=True)
            return series
        else:
            series[keys] = str_values
            return series

    t = series
    series = t.astype(str)
    series[t.isna()] = np.nan
    series[keys] = str_values

    return series


def migrate_params_v0_to_v1(params):
    """
    v0: celledits is a string of JSON

    v1: celledits is an Array of { row, col, value }
    """
    if not params["celledits"]:  # empty str
        celledits = []
    else:
        celledits = json.loads(params["celledits"])
        # [adamhooper, 2019-03-13] seen on production: Numeric values. No idea
        # how they got there. v1 is str-only.
        for celledit in celledits:
            celledit["value"] = str(celledit["value"])

    return {"celledits": celledits}


def migrate_params(params):
    if isinstance(params["celledits"], str):
        params = migrate_params_v0_to_v1(params)

    return params


# Execute our edits. Stored in parameter as an array like this:
#  [
#    { 'row': 3, 'col': 'foo', 'value':'bar' },
#    { 'row': 6, 'col': 'food', 'value':'sandwich' },
#    ...
#  ]
def render(table, params, **kwargs):
    edits = [Edit(**item) for item in params["celledits"]]

    # Ignore missing columns and rows: delete them from the Array of edits
    colnames = set(table.columns)
    nrows = len(table)
    edits = [
        edit
        for edit in edits
        if edit.col in colnames and edit.row >= 0 and edit.row < nrows
    ]

    for column, column_edits in groupby(edits, lambda e: e.col):
        series = table[column]
        series2 = apply_edits(series, list(column_edits))
        if series2 is not series:
            table[column] = series2

    return table
