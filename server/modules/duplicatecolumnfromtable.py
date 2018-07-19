from .moduleimpl import ModuleImpl
from .types import ProcessResult
import pandas as pd

duplicate_column_prefix = 'Copy of'

def _do_render(table, columns):
    cols = columns.split(',')
    cols = [c.strip() for c in cols]

    # if no column has been selected, return table
    if cols == [] or cols == ['']:
        return ProcessResult(table)

    for c in cols:
        new_column_name = '{0} {1}'.format(duplicate_column_prefix, c)

        # Append numbers if column name happens to exist
        if new_column_name in list(table.columns):
            count = 0
            while True:
                count += 1
                if '{0} {1}'.format(new_column_name, count) not in list(table.columns):
                    new_column_name = '{0} {1}'.format(new_column_name, count)
                    break

        table[new_column_name] = table[c]

    return ProcessResult(table)


class DuplicateColumnFromTable(ModuleImpl):
    def render(wf_module, table):
        columns = wf_module.get_param_string('colnames')

        return _do_render(table, columns)
