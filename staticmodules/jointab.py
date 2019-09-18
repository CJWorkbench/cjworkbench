from typing import List, Set


def _parse_colnames(val: List[str], valid: Set[str]):
    return [c for c in val if c in valid]


def render(table, params, *, input_columns):
    right_tab = params["right_tab"]
    if right_tab is None:
        # User hasn't chosen tabs yet
        return table

    right_dataframe = right_tab.dataframe
    on_columns = _parse_colnames(
        params["join_columns"]["on"],
        # Workbench doesn't test whether the 'on' columns are in
        # right_dataframe, but the UI does so we can just ignore any invalid
        # columns and call it a day.
        set(table.columns & right_dataframe.columns),
    )
    right_columns_set = set(
        _parse_colnames(
            params["join_columns"]["right"],
            set(right_dataframe.columns).difference(set(on_columns)),
        )
    )
    # order right_columns as they're ordered in right_dataframe
    right_columns = [c for c in right_dataframe.columns if c in right_columns_set]

    join_type = params["type"]

    # Ensure all "on" types match
    for colname in on_columns:
        left_type = input_columns[colname].type
        right_type = right_tab.columns[colname].type
        if left_type != right_type:
            return (
                f'Column "{colname}" is *{left_type}* in this tab '
                f"and *{right_type}* in {right_tab.name}. Please convert "
                "one or the other so they are both the same type."
            )

    # Ensure we don't overwrite a column (the user won't want that)
    for colname in right_columns:
        if colname in input_columns:
            return (
                f'You tried to add "{colname}" from {right_tab.name}, but '
                "your table already has that column. Please rename the column "
                "in one of the tabs, or unselect the column."
            )

    if not on_columns:
        # Pandas ValueError: not enough values to unpack (expected 3, got 0)
        #
        # Let's pretend we want this behavior, and just pass the input
        # (suggesting to the user that the params aren't all entered yet).
        return table

    for on_column in on_columns:
        # if both 'left' and 'right' are categorical, coerce the categories to
        # be identical, so DataFrame.merge can preserve the Categorical dtype.
        # In cases where Categorical is the dtype we want, the join will be
        # faster and the result will take less RAM and disk space.
        #
        # If we don't do this, the result will have 'object' dtype.
        left_series = table[on_column]
        right_series = right_dataframe[on_column]
        if hasattr(left_series, "cat") and hasattr(right_series, "cat"):
            # sorted for ease of unit-testing
            categories = sorted(
                list(
                    frozenset.union(
                        frozenset(left_series.cat.categories),
                        frozenset(right_series.cat.categories),
                    )
                )
            )
            left_series.cat.set_categories(categories, inplace=True)
            right_series.cat.set_categories(categories, inplace=True)

    # Select only the columns we want
    right_dataframe = right_dataframe[on_columns + right_columns]

    dataframe = table.merge(right_dataframe, on=on_columns, how=join_type)

    colnames_to_recategorize = None
    if join_type == "left":
        colnames_to_recategorize = on_columns + right_columns
    elif join_type == "right":
        colnames_to_recategorize = list(input_columns.keys())
    else:
        colnames_to_recategorize = dataframe.columns
    for colname in colnames_to_recategorize:
        series = dataframe[colname]
        if hasattr(series, "cat"):
            series.cat.remove_unused_categories(inplace=True)

    return {
        "dataframe": dataframe,
        "column_formats": {c: right_tab.columns[c].format for c in right_columns},
    }


def _migrate_params_v0_to_v1(params):
    """
    v0: 'type' is index into ['left', 'inner', 'right']; 'join_columns' are
    comma-separated strs.

    v1: 'type' is one of {'left', 'inner', 'right'}; 'join_columns' are
    List[str].
    """
    return {
        **params,
        "join_columns": {
            "on": [c for c in params["join_columns"]["on"].split(",") if c],
            "right": [c for c in params["join_columns"]["right"].split(",") if c],
        },
        "type": ["left", "inner", "right"][params["type"]],
    }


def migrate_params(params):
    if isinstance(params["type"], int):
        params = _migrate_params_v0_to_v1(params)
    return params
