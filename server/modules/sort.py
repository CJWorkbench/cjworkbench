from cjworkbench.types import ProcessResult
from typing import Any, Dict
import pandas as pd


def _do_render(table, sort_params, keep_top):
    if not sort_params:
        return ProcessResult(table)

    columns = [x['colname'] for x in sort_params]
    directions = [x['is_ascending'] for x in sort_params]

    # check if any column is empty, throw error
    try:
        columns.index('')
        return ProcessResult(dataframe=table, error='Please select a column.')
    except ValueError:
        pass

    # check for duplicate columns
    if len(columns) != len(set(columns)):
        return ProcessResult(dataframe=table, error='Duplicate columns.')

    if keep_top != '':
        try:
            top = int(keep_top)
        except ValueError:
            return ProcessResult(
                dataframe=table,
                error=(
                    'Please enter an integer in "Keep top" or leave it blank.'
                )
            )

        # sort accordingly
        table.sort_values(
            by=columns,
            ascending=directions,
            inplace=True,
            na_position='last'
        )

        # Keep top for first column works differently, keeps top within that
        # column
        if len(columns) < 2:
            columns_to_group = columns
        else:
            columns_to_group = columns[:-1]

        mask = table[columns].isnull().any(axis=1)
        rows_with_na_idx = mask[mask].index
        rows_with_na = table.loc[rows_with_na_idx]
        rows_without_na = table.drop(rows_with_na_idx)

        table = rows_without_na.groupby(columns_to_group).head(top)
        table = pd.concat([table, rows_with_na])

    # sort again with null columns, if any
    table.sort_values(
        by=columns,
        ascending=directions,
        inplace=True,
        na_position='last'
    )

    table.reset_index(drop=True, inplace=True)

    return ProcessResult(table)


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
    sort_params: list = params['sort_columns']
    keep_top: str = params['keep_top']

    return _do_render(table, sort_params, keep_top)
