import pandas as pd


def dropna(table, colnames):
    # convert empty strings to none, because dropna says '' is not na
    try:
        test_table = table[colnames]
    except KeyError as err:
        return 'You chose a missing column'

    # Find rows where any selected column is '' or np.nan
    rows_with_empty = ((test_table == '') | test_table.isna()).any(axis=1)

    table = table[~rows_with_empty]

    # reset index
    table.index = pd.RangeIndex(len(table.index))

    # We may now have unused categories in our category columns. The ''
    # category is an obvious one, and we must certainly remove it from any
    # column in `colnames`. But since we removed entire rows, even categories
    # in _other_ columns may no longer be needed.
    for colname in table.columns:
        series = table[colname]
        if hasattr(series, 'cat'):
            series.cat.remove_unused_categories(inplace=True)

    return table


def render(table, params):
    colnames = list([c for c in params['colnames'].split(',') if c])
    if not colnames:
        return table

    return dropna(table, colnames)
