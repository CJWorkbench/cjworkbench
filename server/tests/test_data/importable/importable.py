def render(table, params):
    col = params['test_column']
    colstring = params['test_multicolumn']

    if col is not None:
        table[col] *= 2

    if colstring is not None:
        cols = colstring.split(',')
        for c in cols:
            table[c] *= 3

    return table

