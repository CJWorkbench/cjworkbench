from .moduleimpl import ModuleImpl
from .utils import parse_json_param

s_map = [',', ';', '\t', '\n']


def parse_list(params, table):
    list_string: str = params['list_string']
    if not list_string:
        return table

    table_width = len(table.columns)
    separator_counts = [list_string.count(x) for x in s_map]

    if sum(separator_counts) == 0:
        return (table, 'Separator between names not detected.')

    separator = s_map[separator_counts.index(max(separator_counts))]
    # Strip values and remove null values
    new_columns = [x.strip()
                   for x in list_string.split(separator) if x.strip()]

    if table_width < len(new_columns):
        return (
            table,
            (
                f'You supplied {len(new_columns)} column names, '
                f'but the table has {table_width} columns'
            )
        )
    elif table_width > len(new_columns):
        new_columns = fill_column_names(new_columns, table_width)

    try:
        table.columns = new_columns
        return table
    except Exception as e:
        return(table, str(e.args[0]))


def fill_column_names(column_names, expected_length):
    start = len(column_names) + 1
    for x in range(start, expected_length + 1):
        proposed_name = f'Column {x}'
        proposed_name_prefix = proposed_name
        num_attempt = 1
        while proposed_name in column_names:
            proposed_name = f'{proposed_name_prefix}_{num_attempt}'
            num_attempt += 1
        column_names.append(proposed_name)
    return column_names


class RenameFromTable(ModuleImpl):
    # Rename entry structure: Dictionary of {old_name: new_name}
    @staticmethod
    def render(params, table, **kwargs):
        custom_list: bool = params['custom_list']
        if not custom_list:
            entries = parse_json_param(params['rename-entries'])

            og_columns = table.columns.tolist()
            new_columns = [entries.get(col, col) for col in og_columns]
            table.columns = new_columns
            return table
        else:
            # XXX [adamhooper, 2019-01-31] rename this function. What does it
            # do?
            return parse_list(params, table)
