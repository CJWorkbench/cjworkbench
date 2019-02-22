from cjworkbench.types import ProcessResult
from typing import Any, Dict

def _do_render(table, sort_params):

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

    table.sort_values(
        by=columns,
        ascending=directions,
        inplace=True,
        na_position='last'
    )

    table.reset_index(drop=True, inplace=True)

    return ProcessResult(table)


_SortAscendings = {
    0: None,
    1: True,
    2: False
}

def _migrate_params_v0_to_v1(column: str, direction: int) -> Dict[str, Any]:
    """
    v0:
    params: {
        column: 'A',
        direction: 1
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
    # Reduce sort options from 2 to 3, anything but 1 is ascending
    is_ascending = direction != 2
    return {
        'sort_columns':
            [{'colname': column, 'is_ascending': is_ascending}]
    }


def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse deprecated sort parameters. Previously sorted 1 column,
    with sort direction as an integrer of either 0, 1, 2 as mapped in
    _SortAscendings.
    """

    if 'sort_columns' not in params:
        try:
            column = params['column']
        except KeyError:
            raise ValueError('Sort is missing "column" key')
        try:
            direction = params['direction']
        except KeyError:
            raise ValueError('Sort is missing "direction" key')
        is_v0 = True
    else:
        is_v0 = False

    if is_v0:
        params = _migrate_params_v0_to_v1(column, direction)

    return params


def render(table, params):    #column: str = params['column']
    sort_params: list = params['sort_columns']

    return _do_render(table, sort_params)
