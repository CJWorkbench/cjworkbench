def render(table, params):
    string = params["test"]
    col = params["test_column"]
    cols = params["test_multicolumn"]

    if string == "crashme":
        raise ValueError("we crashed!")

    if col:
        table[col] *= 2

    if cols:
        table[cols] *= 3

    return table
