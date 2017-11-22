# this python has a syntax error

def render(table, params):
    cols = params['colnames'].split(','
    cols = [c.strip() for c in cols]
    if cols == [] or cols == ['']:
        return table

    newtab = table.dropna(subset=cols, how='all', axis='index')
    return newtab