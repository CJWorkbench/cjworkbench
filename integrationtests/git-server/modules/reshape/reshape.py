def render(table, params):
    import pandas as pd

    diridx = params['direction']
    cols = params.get('colnames', '')
    varcol = params.get('varcol', '')

    # no columns selected and not transpose, NOP
    if cols=='' and diridx != 2:
        return table
    cols = cols.split(',')

    dirmap = ['widetolong', 'longtowide', 'transpose']  # must match reshape.json
    dir = dirmap[diridx]

    if dir == 'widetolong':
        table = pd.melt(table, id_vars=cols)
        table.sort_values(cols, inplace=True)
        table = table.reset_index(drop=True)  # renumber after sort, don't add extra index col

    elif dir == 'longtowide':
        if varcol == '':            # gotta have this parameter
            return table

        keys = cols

        has_second_key = params.get('has_second_key', False)
        # If second key is used and present, append it to the list of columns
        if has_second_key:
            second_key = params.get('second_key', '')
            if second_key in table.columns:
                keys.append(second_key)

        table = table.set_index(keys + [varcol]).unstack()
        table.columns = [col[-1] for col in table.columns.values]
        table = table.reset_index()

    elif dir == 'transpose':
        # We assume that the first column is going to be the new header row
        # Use the content of the first column (including header) as the new headers
        new_columns = [table.columns[0]] + table[table.columns[0]].tolist()
        index_col = table.columns[0]
        # Transpose table, reset index and correct column names
        table = table.set_index(index_col).transpose().reset_index()
        table.columns = new_columns
        # Infer data type of each column (numeric or string)
        for col in table.columns:
            try:
                table[col] = pd.to_numeric(table[col], errors='raise')
            except:
                table[col] = table[col].astype(str)

    return table
