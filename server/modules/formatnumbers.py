def render(table, params):
    colnames = params["colnames"]
    if not colnames:
        return table

    # Don't edit `table` at all. Just set new column_formats.
    return {
        "dataframe": table,
        "column_formats": {c: params["format"] for c in colnames},
    }


def _migrate_params_v0_to_v1(params):
    """v0: colnames is comma-separated str. v1: colnames is List[str]."""
    return {
        "colnames": [c for c in params["colnames"].split(",") if c],
        "format": params["format"],
    }


def migrate_params(params):
    if isinstance(params["colnames"], str):
        params = _migrate_params_v0_to_v1(params)
    return params
