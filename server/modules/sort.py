from cjworkbench.types import ProcessResult
from typing import Any, Dict

def _do_render(table, sort_params, keep_top):

    if not sort_params:
        return ProcessResult(table)

    # when user has yet to choose the first column
    if len(sort_params) == 1 and sort_params[0]['colname'] == '':
        return ProcessResult(dataframe=table, error='Please select a column.')

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

    if keep_top != '':
        try:
            top = int(keep_top)
        except:
            return ProcessResult(dataframe=table, error='Please enter an integer in "Keep top" or leave it blank.')

        table = table.groupby(columns).head(top)

    return ProcessResult(table)


_SortAscendings = {
    0: None,
    1: True,
    2: False
}

def migrate_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse deprecated sort parameters. Previously sorted 1 column,
    with sort direction as an integrer of either 0, 1, 2 as mapped in
    _SortAscendings.

    v0:

    params: {
        column: 'A',
        direction: 1
    }

    v1:

    params: {
        sort_columns: [
            { colname: 'A', is_ascending: True },
            { colname: 'B', is_ascending: False}
        ],
        keep_top: '2'
    }

    """
    if 'sort_columns' not in params:
        try:
            colname = params['column']
        except KeyError:
            raise ValueError('Sort is missing "column" key')
        try:
            # Reduce sort options from 2 to 3, anything but 1 is ascending
            is_ascending = params['direction'] != 2
        except KeyError:
            raise ValueError('Sort is missing "direction" key')

        return { 'sort_columns': [{ 'colname': colname, 'is_ascending': is_ascending}], 'keep_top': ''}
    else:
        return params


def render(table, params):    #column: str = params['column']
    sort_params: list = params['sort_columns']
    keep_top: str = params['keep_top']

    return _do_render(table, sort_params, keep_top)
