from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import parse_multicolumn_param


def _do_render(table, dup_columns):
    colnames = set(table.columns)

    for c in dup_columns:
        new_column_name = f'Copy of {c}'

        # Append numbers if column name happens to exist
        count = 0
        try_column_name = new_column_name
        while try_column_name in colnames:
            count += 1
            try_column_name = f'{new_column_name} {count}'
        new_column_name = try_column_name
        colnames.add(new_column_name)

        # Add new column next to reference column
        column_idx = table.columns.tolist().index(c)
        table.insert(column_idx + 1, new_column_name, table[c])

    return ProcessResult(table)


class DuplicateColumn(ModuleImpl):
    def render(params, table, **kwargs):
        columns, _ = parse_multicolumn_param(params['colnames'], table)

        return _do_render(table, columns)
