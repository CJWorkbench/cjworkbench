# --- Dataframe sanitization and truncation ---
from typing import Any, List, Optional
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


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
