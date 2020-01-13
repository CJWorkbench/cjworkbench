def _isempty(series):
    na = series.isna()

    if hasattr(series, "cat") or series.dtype == object:
        # string series: '' and None are the ones to delete
        empty = series == ""
        return (na | empty).all()
    else:
        # non-string: NA is the only thing to delete
        return na.all()


def render(table, params):
    dropcols = [c for c in table.columns if _isempty(table[c])]
    table = table.drop(dropcols, axis=1)
    return table


def _migrate_params_v0_to_v1(params):
    """
    v0: had "nulldropper_statictext" key (with no data)

    v1: there are no params
    """
    return {}


def migrate_params(params):
    if "nulldropper_statictext" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
