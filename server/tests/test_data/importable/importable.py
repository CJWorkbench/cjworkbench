def render(table, params):
    col = params['test_column']
    colstring = params['test_multicolumn']

    if col != '':
        table[col] *= 2

    if colstring != '':
        cols = colstring.split(',')
        for c in cols:
            table[c] *= 3

    return table

