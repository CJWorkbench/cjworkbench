# --- Dataframe sanitization and truncation ---
import pandas as pd

# convert numbers to string, replacing NaN with '' (naive conversion results in 'Nan' string cells)
def safe_column_to_string(col):
    def string_or_null(val):
        if isinstance(val, list) or isinstance(val, dict):
            return str(val)
        elif pd.isnull(val):  # this expression won't work on containers
            return ''
        else:
            return str(val)

    return col.apply(string_or_null)


# Ensure floats are displayed with as few zeros as possible
def colname_to_str(c):
    if isinstance(c, float):
        return '%g' % c
    else:
        return str(c)


# Convert all complex-typed rows to strings. Otherwise we cannot do many operations
# including hash_pandas_object() and to_parquet()
# Also rename duplicate columns
def sanitize_dataframe(table):
    if table is None:
        return pd.DataFrame()

    # full type list at https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
    allowed_types = ['string', 'floating', 'integer', 'categorical', 'boolean', 'datetime', 'date', 'time']
    types = table.apply(pd.api.types.infer_dtype)
    for idx, val in enumerate(types):
        if val not in allowed_types:
            table.iloc[:, idx] = safe_column_to_string(table.iloc[:, idx])

    # force string column names, and uniquify by appending a number
    newcols = []
    for item in table.columns:
        counter = 0
        newitem = colname_to_str(item)
        while newitem in newcols:
            counter += 1
            newitem = newitem + '_' + str(counter)
        newcols.append(newitem)
    table.columns = newcols

    # renumber row indices so always 0..n
    table.index = pd.RangeIndex(len(table.index))

    return table


def truncate_table_if_too_big(df):
    """
    Limit table size to max allowed number of rows.

    Return whether we modified the table.
    """
    # Import here, so that the pythoncode module does not need to import django
    from django.conf import settings

    nrows = len(df)
    if nrows > settings.MAX_ROWS_PER_TABLE:
        df.drop(range(settings.MAX_ROWS_PER_TABLE, nrows), inplace=True)
        return True
    else:
        return False
