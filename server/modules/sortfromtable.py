from .moduleimpl import ModuleImpl
from .types import ProcessResult


def _do_render(table, column, is_ascending):
    if not column or column not in table.columns:
        return ProcessResult(table)

    if is_ascending is None:  # Why do we even _have_ that lever?
        return ProcessResult(table)

    values = table[column]

    # Add temporary column for sorting. Pick unique name: just take the last
    # name and add a letter.
    tmp_sort_col = max(table.columns) + 'ZZZ'
    table[tmp_sort_col] = values
    table.sort_values(
        by=tmp_sort_col,
        ascending=is_ascending,
        inplace=True,
        na_position='last'
    )
    table.drop(columns=[tmp_sort_col], inplace=True)
    table.reset_index(inplace=True, drop=True)

    return ProcessResult(table)


_SortAscendings = {
    0: None,
    1: True,
    2: False
}


class SortFromTable(ModuleImpl):
    def render(params, table, **kwargs):
        column: str = params['column']

        is_ascending_int: int = params['direction']
        is_ascending = _SortAscendings.get(is_ascending_int, None)  # yep: None

        return _do_render(table, column, is_ascending)
