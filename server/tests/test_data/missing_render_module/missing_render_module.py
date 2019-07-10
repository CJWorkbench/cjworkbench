# valid python, but does not have required render funtion


def not_render(table, params):
    cols = params["colnames"].split(",")
    cols = [c.strip() for c in cols]
    if cols == [] or cols == [""]:
        return table

    newtab = table.dropna(subset=cols, how="all", axis="index")
    return newtab
