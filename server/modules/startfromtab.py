def render(table, params):
    tab = params["tab"]

    if tab is None:
        return None

    return {
        "dataframe": tab.dataframe,
        "column_formats": {
            c.name: c.format for c in tab.columns.values() if c.format is not None
        },
    }
