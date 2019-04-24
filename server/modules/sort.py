from dataclasses import dataclass
from typing import Any, Dict, List, Union
import pandas as pd


@dataclass
class SortColumn:
    """Entry in the `sort_columns` (List) param."""
    colname: str
    is_ascending: bool


def _do_render(
    table, *,
    sort_columns: List[Dict[str, Union[str, bool]]],
    keep_top: str
):
    # Filter out empty columns (don't raise an error)
    sort_columns = [SortColumn(**sc) for sc in sort_columns if sc['colname']]

    if keep_top:
        try:
            keep_top_int = int(keep_top)
            if keep_top_int <= 0:
                raise ValueError
        except ValueError:
            return (
                'Please enter a positive integer in "Keep top" '
                'or leave it blank.'
            )
    else:
        keep_top_int = None

    if not sort_columns:
        return table

    columns = [sc.colname for sc in sort_columns]
    directions = [sc.is_ascending for sc in sort_columns]

    # check for duplicate columns
    if len(columns) != len(set(columns)):
        # TODO support this case? The intent is unambiguous.
        return 'Duplicate columns.'

    if keep_top_int and len(sort_columns) > 1:
        # sort by _last_ column: that's the sorting we'll use within each group
        table.sort_values(
            by=sort_columns[-1].colname,
            ascending=sort_columns[-1].is_ascending,
            inplace=True,
            na_position='last'
        )

        columns_to_group = columns[:-1]
        rows_with_na_mask = table[columns_to_group].isnull().any(axis=1)
        rows_with_na = table[rows_with_na_mask]
        rows_without_na = table[~rows_with_na_mask]

        keep_grouped_rows = (
            rows_without_na
            .groupby(columns_to_group, sort=False)
            .head(keep_top_int)
        )
        table = pd.concat([keep_grouped_rows, rows_with_na], ignore_index=True)

    # sort values
    table.sort_values(
        by=columns,
        ascending=directions,
        inplace=True,
        na_position='last'
    )

    if keep_top_int and len(sort_columns) == 1:
        # The whole result is one big group, and we want to keep the elements
        # within it.
        table = table.head(keep_top_int)

    table.reset_index(drop=True, inplace=True)

    if keep_top_int:
        # We may have removed rows. Now, tidy up all Categorical columns.
        for column in table.columns:
            series = table[column]
            if hasattr(series, 'cat'):
                series.cat.remove_unused_categories(inplace=True)

    return table


def _migrate_params_v0_to_v1(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    v0:
    params: {
        column: 'A',
        direction: 1  # 0: 'None' [sic], 1: 'Ascending', 2: 'Descending'
    }

    v1:
    params: {
        sort_columns: [
            {colname: 'A', is_ascending: True},
            {colname: 'B', is_ascending: False}
        ],
        keep_top: '2'
    }
    """
    return {
        'sort_columns': [
            {
                'colname': params['column'],
                # Reduce sort options from 2 to 3, anything but 1 is ascending
                'is_ascending': params['direction'] != 2,
            },
        ],
    }


def _migrate_params_v1_to_v2(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add the 'keep_top' param

    v1:
    params: {
        sort_columns: [
            {colname: 'A', is_ascending: True},
            {colname: 'B', is_ascending: False}
        ]
    }

    v2:
    params: {
        sort_columns: [
            {colname: 'A', is_ascending: True},
            {colname: 'B', is_ascending: False}
        ],
        keep_top: '2'
    }
    """
    params['keep_top'] = ''
    return params


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    if 'sort_columns' not in params:
        params = _migrate_params_v0_to_v1(params)

    if 'keep_top' not in params.keys():
        params = _migrate_params_v1_to_v2(params)

    return params


def render(table, params):
    return _do_render(table, **params)
