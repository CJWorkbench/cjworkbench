from .moduleimpl import ModuleImpl
from .types import ProcessResult
import pandas as pd


def _do_render(table, column, column_type, is_ascending):
    if not column or column not in table.columns:
        return ProcessResult(table)

    if is_ascending is None:  # Why do we even _have_ that lever?
        return ProcessResult(table)

    untyped_values = table[column]
    if column_type == 'String':
        typed_values = untyped_values.astype(str)
    elif column_type == 'Number':
        typed_values = pd.to_numeric(untyped_values, errors='coerce')
    elif column_type == 'Date':
        typed_values = pd.to_datetime(untyped_values, errors='coerce')
    else:
        typed_values = untyped_values

    # Add temporary column for sorting. Pick unique name: just take the last
    # name and add a letter.
    tmp_sort_col = max(table.columns) + 'ZZZ'
    table[tmp_sort_col] = typed_values
    table.sort_values(
        by=tmp_sort_col,
        ascending=is_ascending,
        inplace=True,
        na_position='last'
    )
    table.drop(columns=[tmp_sort_col], inplace=True)
    table.reset_index(inplace=True, drop=True)

    return ProcessResult(table)


_SortTypes = {
    0: 'String',
    1: 'Number',
    2: 'Date',
}
_SortAscendings = {
    0: True,
    1: False
}


class SortFromTable(ModuleImpl):
    def render(wf_module, table):
        column = wf_module.get_param_column('column')

        sort_type_int = int(wf_module.get_param_menu_idx('dtype'))
        sort_type = _SortTypes.get(sort_type_int, 'String')

        is_ascending_int = int(wf_module.get_param_menu_idx('direction'))
        is_ascending = _SortAscendings.get(is_ascending_int, None)  # yep: None

        return _do_render(table, column, sort_type, is_ascending)
