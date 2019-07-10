def render(table, params):
    newcol = params["newcolumn"]
    if newcol != "":
        cols = params["colnames"].split(",")
        cols = [c.strip() for c in cols]
        if cols != [] and cols != [""]:
            table[newcol] = table[cols].apply(
                lambda x: " ".join([str(i) for i in x if str(i) != "nan"]), axis=1
            )
    return table
