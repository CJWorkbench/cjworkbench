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
        return "%g" % c
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
        backup_name = f"{ideal_name}_{count}"
        return unique_name(backup_name)

    return [unique_name(_colname_to_str(c)) for c in colnames]


def sanitize_series(series: pd.Series) -> pd.Series:
    """
    Enforce type rules on input pandas `Series.values`.

    The return value is anything that can be passed to the `pandas.Series()`
    constructor.

    Specific fixes:

    * Make sure categories have no excess values.
    * Convert numeric categories to 
    * Convert unsupported dtypes to string.
    * Reindex so row numbers are contiguous.
    """
    series.reset_index(drop=True, inplace=True)
    if hasattr(series, "cat"):
        series.cat.remove_unused_categories(inplace=True)

        categories = series.cat.categories
        if pd.api.types.is_numeric_dtype(categories.values):
            # Un-categorize: make array of int/float
            return pd.to_numeric(series)
        elif (
            categories.dtype != object
            or pd.api.types.infer_dtype(categories.values, skipna=True) != "string"
        ):
            # Map from non-Strings to Strings
            #
            # 1. map the _codes_ to unique _codes_
            mapping = pd.Categorical(categories.astype(str))
            values = pd.Categorical(series.cat.codes[mapping.codes])
            # 2. give them names
            values.rename_categories(mapping.categories, inplace=True)
            series = pd.Series(values)

        return series
    elif is_numeric_dtype(series.dtype):
        return series
    elif is_datetime64_dtype(series.dtype):
        return series
    else:
        # Force it to be a str column: every object is either str or np.nan
        ret = series.astype(str)
        ret[pd.isna(series)] = np.nan
        return ret


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
