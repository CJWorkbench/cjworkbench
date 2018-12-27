def render(table, params):
    import pandas as pd # needed for tests to run, ugly in production
    import numpy as np

    if table is None:
        return None

    # first drop cols where all are None or NaN
    table.dropna(axis=1, how='all', inplace=True)

    # Now drop cols where all are empty string
    keepcols = []
    str_dtypes = ['object', 'category']
    for c in table.columns:
        if not ((table[c].dtype.name in str_dtypes) and (table[c]=='').all()):
            keepcols.append(c)

    if len(keepcols) != len(table.columns):
        table = table[keepcols]

    return table
