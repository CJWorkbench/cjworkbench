def render(table, params, *, input_columns):
    colnames = [c for c in params['colnames'].split(',') if c]

    if not colnames:
        return table

    for colname in colnames:
        coltype = input_columns[colname].type
        if coltype != 'number':
            return (
                'Cannot format column "%s" because it is of type "%s".'
                % (colname, coltype)
            )

    # Don't edit `table` at all. Just set new column_formats.
    return {
        'dataframe': table,
        'column_formats': {c: params['format'] for c in colnames}
    }
