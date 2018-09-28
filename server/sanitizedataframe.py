# --- Dataframe sanitization and truncation ---
from typing import Any, List, Optional
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


def _colname_to_str(c: Any) -> str:
    """
    Cast a column name to str.

    In the case of a float column name, this method optimizes for the fewest
    zeros possible.
    """
    if isinstance(c, float):
        return '%g' % c
    else:
        # need to strip col names to stay in sync with column selection modules
        return str(c).strip()


def _normalize_colnames(colnames: List[Any]) -> None:
    """
    Modify column names so they are all unique and str.
    """
    counts = {}

    def unique_name(ideal_name: str) -> str:
        """
        Generate a guaranteed-unique column name, using `counts` as state.

        Strategy for making 'A' unique:

        * If 'A' has never been seen before, return it.
        * If 'A' has been seen before, try 'A_1' or 'A_2' (where 1 and 2 are
          the number of times 'A' has been seen).
        * If there is a conflict on 'A_1', recurse.
        """
        if ideal_name not in counts:
            counts[ideal_name] = 1
            return ideal_name

        count = counts[ideal_name]
        counts[ideal_name] += 1
        backup_name = f'{ideal_name}_{count}'
        return unique_name(backup_name)

    return [unique_name(_colname_to_str(c)) for c in colnames]


# full type list:
# https://pandas.pydata.org/pandas-docs/stable/generated/pandas.api.types.infer_dtype.html
_AllowedDtypes = {
    'boolean',
    # categorical is a special case
    'date',
    'datetime',
    'floating',
    'integer',
    'string',
    'time',
}


def sanitize_values(values):
    """
    Enforce type rules on input pandas `Series.values`.

    The return value is anything that can be passed to the `pandas.Series()`
    constructor.

    Specific fixes:

    * Make sure categories have no excess values.
    * Convert numeric categories to 
    * Convert unsupported dtypes to string.
    """
    if hasattr(values, 'categories'):
        categories = values.categories
        if pd.api.types.is_numeric_dtype(categories.values):
            # Un-categorize: make array of int/float
            return pd.to_numeric(values)
        elif categories.dtype != object \
                or pd.api.types.infer_dtype(categories.values) != 'string':
            # Cast non-Strings to String
            values.rename_categories(categories.astype(str), inplace=True)

        values.remove_unused_categories(inplace=True)
        return values
    elif is_numeric_dtype(values.dtype):
        return values
    elif is_datetime64_dtype(values.dtype):
        return values
    else:
        # Force it to be a str column: every object is either str or np.nan
        ret = pd.Series(values).astype(str).values
        ret[pd.isna(values)] = np.nan
        return ret


def sanitize_dataframe(table: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Modify table in-place to conform to Workbench data types.

    After calling this method on a table, `hash_pandas_object()` will work and
    writing to parquet format will be viable.

    Specific fixes:

    * Convert `None` to an empty DataFrame.
    * Modify duplicate column names.
    * Reindex so row numbers are contiguous.
    * Convert unsupported dtypes to string.
    """
    if table is None:
        return pd.DataFrame()

    table.reset_index(drop=True, inplace=True)

    colnames = _normalize_colnames(table.columns)
    table.columns = _normalize_colnames(colnames)

    # Ignore spurious SettingWithCopyWarning
    #
    # Also, the SettingWithCopyWarning test runs a gc cycle, which is slow.
    # [adamhooper, 2018-09-28] A slew of sanitize tests dropped from 0.67s to
    # 0.48s when I changed mode.chained_assignment to None.
    with pd.option_context('mode.chained_assignment', None):
        # Sanitize one column at a time: that's more memory-friendly
        for colname in colnames:
            table[colname] = sanitize_values(table[colname].values)

    return table


def autocast_series_dtype(series: pd.Series) -> pd.Series:
    """
    Cast str/object series to numeric, if possible.

    This is appropriate when parsing CSV data, or maybe Excel data. It _seems_
    appropriate when a search-and-replace produces numeric columns like
    '$1.32' => '1.32' ... but perhaps that's only appropriate in very-specific
    cases.

    TODO handle dates and maybe booleans.
    """
    if series.dtype == 'O':
        # Object (str) series. Try to infer type.
        #
        # We don't case from complex to simple types here: we assume the input
        # is already sane.
        try:
            return pd.to_numeric(series)
        except ValueError:
            return series
    elif hasattr(series, 'cat'):
        # Categorical series. Try to infer type of series.
        try:
            # Replace empty str with nan -- will help to_numeric
            if '' in series.cat.categories:
                series = series.cat.remove_categories([''])
            categories = pd.to_numeric(series.cat.categories)
            series.cat.rename_categories(categories, inplace=True)
            # Expand categories. This will likely save space for int8 and cost
            # space for float64. [2018-07-3] The only strong rationale at the
            # moment (either for or against this approach) is simplifying unit
            # tests.
            return series.astype(series.cat.categories.dtype)
        except ValueError as err:
            return series
    # Setting dtype=None in read_csv infers types, must account for numerical series
    # otherwise sets column to null
    else:
        return series

def autocast_dtypes_in_place(table: pd.DataFrame) -> None:
    """
    Cast str/object columns to numeric, if possible.

    This is appropriate when parsing CSV data, or maybe Excel data. It is
    probably not appropriate to call this method elsewhere, since it destroys
    data types all over the table.

    TODO handle dates and maybe booleans.
    """
    for colname in table:
        column = table[colname]
        table[colname] = autocast_series_dtype(column)


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
