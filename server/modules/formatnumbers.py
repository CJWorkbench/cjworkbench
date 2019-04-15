def render(table, params):
    colnames = [c for c in params['colnames'].split(',') if c]

    if not colnames:
        return table

    # Don't edit `table` at all. Just set new column_formats.
    return {
        'dataframe': table,
        'column_formats': {c: params['format'] for c in colnames}
    }
