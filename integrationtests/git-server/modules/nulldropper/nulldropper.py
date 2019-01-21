def _isempty(series):
    na = series.isna()

    if hasattr(series, 'cat') or series.dtype == object:
        # string series: '' and None are the ones to delete
        empty = (series == '')
        return (na | empty).all()
    else:
        # non-string: NA is the only thing to delete
        return na.all()


def render(table, params):
    dropcols = [c for c in table.columns if _isempty(table[c])]
    table = table.drop(dropcols, axis=1)
    return table
