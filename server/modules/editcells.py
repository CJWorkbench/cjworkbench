from itertools import groupby
from typing import List, Union
import pandas as pd
import numpy as np
from .moduleimpl import ModuleImpl
from server.models import WfModule
import json
import logging
from server.sanitizedataframe import safe_column_to_string

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

    if series.dtype == np.int64 or series.dtype == np.float64:
        try:
            num_values = pd.to_numeric(str_values)
            # pandas will upcast int64 col to float64 if needed
            series[keys] = num_values
        except ValueError:
            # convert numbers to string, replacing NaN with ''
            series = safe_column_to_string(series)
            series[keys] = str_values
    elif hasattr(series, 'cat'):
        series.cat.add_categories(set(str_values) - set(series.cat.categories),
                                  inplace=True)
        series[keys] = str_values
    else:
        if series.dtype != np.object:
            logger.warning('Unknown Pandas column type %s in edit cells' %
                           str(series.dtype))

        # Column type is str (see sanitize_dataframe) so assign directly
        series[keys] = str_values

    return series


def parse_json(edits_str: str) -> Union[List[Edit], str]:
    """Parse a list of Edits from a str, or return an error string."""
    if edits_str == '':
        return []

    try:
        edits_arr = json.loads(edits_str)
    except json.JSONDecodeError as str:
        return f'Internal error: invalid JSON'

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
    def render(wfm: WfModule,
               table: pd.DataFrame) -> Union[str, pd.DataFrame]:
        edits = parse_json(wfm.get_param_raw('celledits', 'custom'))
        if isinstance(edits, str):
            return edits

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
