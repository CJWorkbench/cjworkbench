from typing import Set


def _parse_colnames(s: str, valid: Set[str]):
    return [c for c in s.split(',') if c in valid]


def render(table, params, *, input_columns):
    right_tab = params['right_tab']
    if right_tab is None:
        # User hasn't chosen tabs yet
        return table

    right_dataframe = right_tab.dataframe
    on_columns = _parse_colnames(
        params['join_columns']['on'],
        # Workbench doesn't test whether the 'on' columns are in
        # right_dataframe, but the UI does so we can just ignore any invalid
        # columns and call it a day.
        set(table.columns & right_dataframe.columns)
    )
    right_columns_set = set(_parse_colnames(
        params['join_columns']['right'],
        set(right_dataframe.columns)
    ))
    # order right_columns as they're ordered in right_dataframe
    right_columns = [c for c in right_dataframe.columns
                     if c in right_columns_set]

    join_type = ['left', 'inner', 'right'][params['type']]

    # Ensure all "on" types match
    for colname in on_columns:
        left_type = input_columns[colname].type
        right_type = right_tab.columns[colname].type
        if left_type != right_type:
            return (
                f'Column "{colname}" is *{left_type}* in this tab '
                f'and *{right_type}* in {right_tab.name}. Please convert '
                'one or the other so they are both the same type.'
            )

    # Ensure we don't overwrite a column (the user won't want that)
    for colname in right_columns:
        if colname in input_columns:
            return (
                f'You tried to add "{colname}" from {right_tab.name}, but '
                'your table already has that column. Please rename the column '
                'in one of the tabs, or unselect the column.'
            )

    if not on_columns:
        # Pandas ValueError: not enough values to unpack (expected 3, got 0)
        #
        # Let's pretend we want this behavior, and just pass the input
        # (suggesting to the user that the params aren't all entered yet).
        return table

    # Select only the columns we want
    right_dataframe = right_dataframe[on_columns + right_columns]

    return table.merge(
        right_dataframe,
        on=on_columns,
        how=join_type
    )
