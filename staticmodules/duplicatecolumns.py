def render(table, params, *, input_columns):
    # we'll modify `table` in-place and build up `column_formats`
    column_formats = {}

    colnames = set(table.columns)

    for c in params["colnames"]:
        new_column_name = f"Copy of {c}"

        # Append numbers if column name happens to exist
        count = 0
        try_column_name = new_column_name
        while try_column_name in colnames:
            count += 1
            try_column_name = f"{new_column_name} {count}"
        new_column_name = try_column_name
        colnames.add(new_column_name)

        # Add new column next to reference column
        column_idx = table.columns.tolist().index(c)
        table.insert(column_idx + 1, new_column_name, table[c])
        column_formats[new_column_name] = input_columns[c].format

    return {"dataframe": table, "column_formats": column_formats}


def _migrate_params_v0_to_v1(params):
    """
    v0: 'colnames' is comma-separated str. v1: 'colnames' is List.
    """
    if params["colnames"]:
        return {"colnames": params["colnames"].split(",")}
    else:
        return {"colnames": []}


def migrate_params(params):
    if isinstance(params["colnames"], str):
        params = _migrate_params_v0_to_v1(params)
    return params
