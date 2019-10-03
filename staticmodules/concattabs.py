from collections import namedtuple
import pandas as pd


UsedColumn = namedtuple("UsedColumn", ("type", "tab_name"))


def render(table, params, *, tab_name, input_columns):
    if not params["tabs"]:
        return table

    # Find conflicting columns. Columns are complementary if they have the same
    # type; they conflict if they have different types. Iterate through all
    # tabs, checking the (colname, type, tab_name) trios.
    used_columns = {}
    for colname in table.columns:
        column = input_columns[colname]
        used_columns[colname] = UsedColumn(column.type, tab_name)

    for tab in params["tabs"]:
        for column in tab.columns.values():
            colname = column.name
            if column.name in used_columns:
                used_column = used_columns[column.name]
                if used_column.type != column.type:
                    return (
                        f'Cannot concatenate column "{column.name}" of type '
                        f'"{column.type}" in "{tab.name}" to column '
                        f'"{column.name}" of type "{used_column.type}" in '
                        f'"{used_column.tab_name}". Please convert one or the '
                        "other so they are the same type."
                    )
            else:
                used_columns[column.name] = UsedColumn(column.type, tab.name)

    if params["add_source_column"]:
        source_colname = params["source_column_name"] or "Source"
        if source_colname in used_columns:
            tab_name = used_columns[source_colname].tab_name
            return (
                f'Cannot create column "{source_colname}": "{tab_name}" '
                "already has that column. Please write a different Source "
                "column name."
            )
    else:
        source_colname = None

    to_join = {tab_name: table}
    for tab in params["tabs"]:
        to_join[tab.name] = tab.dataframe

    # second 'names' value must be anything that _isn't_ source_colname. Our
    # hack: 'xxx' + source_colname.
    concatenated = pd.concat(to_join, sort=False, ignore_index=True)

    if source_colname:
        # Add 'source' column as a Categorical. This takes virtually no
        # disk+RAM, as opposed to a str column which can take a lot.
        source_categories = []  # list of tab names
        source_values = []  # list of source_categories indexes
        if len(table):
            source_categories.append(tab_name)
            source_values.extend([0] * len(table))
        for tab in params["tabs"]:
            if len(tab.dataframe):
                source_values.extend([len(source_categories)] * len(tab.dataframe))
                source_categories.append(tab.name)
        sources = pd.Categorical.from_codes(source_values, source_categories)
        concatenated.insert(loc=0, column=source_colname, value=sources)

    return concatenated
