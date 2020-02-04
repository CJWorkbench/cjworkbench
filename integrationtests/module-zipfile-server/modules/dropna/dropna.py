import numpy as np
import pandas as pd


def dropna(table, colnames):
    test_table = table[colnames]

    # Find rows where any selected column is '' or np.nan
    # TODO consider letting users remove np.nan and not ''.
    rows_with_empty = table[colnames].isin([np.nan, pd.NaT, None, '']).any(axis=1)

    table = table[~rows_with_empty]
    table.reset_index(drop=True, inplace=True)

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
    if not params['colnames']:
        return table

    return dropna(table, params['colnames'])


def _migrate_params_v0_to_v1(params):
    """Convert 'colnames' from str to list."""
    # https://www.pivotaltracker.com/story/show/160463316
    return {
        'colnames': [c for c in params['colnames'].split(',') if c]
    }


def migrate_params(params):
    if isinstance(params['colnames'], str):
        params = _migrate_params_v0_to_v1(params)
    return params
