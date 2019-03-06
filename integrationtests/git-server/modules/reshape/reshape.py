import numpy as np
import pandas as pd


def render(table, params):
    dir = params['direction']
    cols = params.get('colnames', '')
    varcol = params.get('varcol', '')

    # no columns selected and not transpose, NOP
    if not cols and dir != 'transpose':
        return table
    cols = cols.split(',')

    if dir == 'widetolong':
        table = pd.melt(table, id_vars=cols)
        table.sort_values(cols, inplace=True)
        table.reset_index(drop=True, inplace=True)

    elif dir == 'longtowide':
        if not varcol:
            # gotta have this parameter
            return table

        keys = cols

        has_second_key = params.get('has_second_key', False)
        # If second key is used and present, append it to the list of columns
        if has_second_key:
            second_key = params.get('second_key', '')
            if second_key in table.columns:
                keys.append(second_key)

        if varcol in keys:
            return 'Cannot reshape: column and row variables must be different'

        table.set_index(keys + [varcol], inplace=True, drop=True)

        if np.any(table.index.duplicated()):
            return 'Cannot reshape: some variables are repeated'

        table = table.unstack()
        table.columns = [col[-1] for col in table.columns.values]
        table.reset_index(inplace=True)

    elif dir == 'transpose':
        # We assume that the first column is going to be the new header row
        # Use the content of the first column as the new headers
        # We set the first column header to 'New Column'. Using the old header
        # is confusing.

        # Check if Column Header Exists in Column
        new_columns = table[table.columns[0]].astype(str).tolist()

        new_colname_prefix = 'New Column'
        new_colname = new_colname_prefix
        suffix = 1
        while new_colname in new_columns:
            new_colname = f'{new_colname_prefix}_{str(suffix)}'
            if new_colname not in new_columns:
                break
            suffix += 1
        new_columns = [new_colname] + new_columns
        index_col = table.columns[0]
        # Transpose table, reset index and correct column names
        table = table.set_index(index_col).transpose()
        # Clear columns in case CategoricalIndex dtype
        table.columns = ['']*len(table.columns)
        table = table.reset_index()
        table.columns = new_columns

    return table


def _migrate_params_v0_to_v1(params):
    # v0: menu item indices. v1: menu item labels
    v1_dir_items = ['widetolong', 'longtowide', 'transpose']
    params['direction'] = v1_dir_items[params['direction']]
    return params


def migrate_params(params):
    # Convert numeric direction parameter to string labels, if needed
    if isinstance(params['direction'], int):
        params = _migrate_params_v0_to_v1(params)

    return params

