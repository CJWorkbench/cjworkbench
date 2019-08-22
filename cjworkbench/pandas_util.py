import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_dtype


SupportedNumberDtypes = frozenset(
    {
        np.dtype("float16"),
        np.dtype("float32"),
        np.dtype("float64"),
        np.dtype("int8"),
        np.dtype("int16"),
        np.dtype("int32"),
        np.dtype("int64"),
        np.dtype("uint8"),
        np.dtype("uint16"),
        np.dtype("uint32"),
        np.dtype("uint64"),
    }
)


def validate_series(series: pd.Series) -> None:
    """
    Ensure `series` is "valid" as per Workbench standards, or raise ValueError.

    "Valid" means:

    * If dtype is `object` or `categorical`, all values are `str`, `np.nan` or
      `None`
    * Otherwise, series must be numeric (but not "nullable integer") or
      datetime (without timezone).
    """
    dtype = series.dtype
    if dtype in SupportedNumberDtypes:
        infinities = series.isin([np.inf, -np.inf])
        if infinities.any():
            idx = series[infinities].index[0]
            raise ValueError(
                ("invalid value %r in column %r, row %r " "(infinity is not supported)")
                % (series[idx], series.name, idx)
            )
        return
    elif is_datetime64_dtype(dtype):  # rejects datetime64ns
        return
    elif dtype == object:
        nonstr = series[~series.isnull()].map(type) != str
        if nonstr.any():
            raise ValueError(
                "invalid value %r in column %r (object values must all be str)"
                % (series.iloc[nonstr[nonstr == True].index[0]], series.name)
            )
    elif hasattr(series, "cat"):
        categories = series.cat.categories
        if categories.dtype != object:
            raise ValueError(
                (
                    "invalid categorical dtype %s in column %r "
                    "(categories must have dtype=object)"
                )
                % (categories.dtype, series.name)
            )
        nonstr = categories.map(type) != str
        if nonstr.any():
            raise ValueError(
                "invalid value %r in column %r (categories must all be str)"
                % (categories[np.flatnonzero(nonstr)[0]], series.name)
            )

        # Detect unused categories: they waste space, and since the module
        # author need only .remove_unused_categories() there isn't much reason
        # to allow them (other than the fact this check might be slow?).
        codes = np.unique(series.cat.codes)  # retval is sorted
        if len(codes) and codes[0] == -1:
            codes = codes[1:]
        # At this point, if all categories are used, `codes` is an Array of
        # [0, 1, ..., len(categories)-1]. Otherwise, there's a "hole" somewhere
        # in `codes` (it may be at the end).
        if len(codes) != len(categories):
            # There are unused categories. That means an index into
            # `categories` is not in `codes`. Raise it.
            for i, category in enumerate(categories):
                if i >= len(codes) or codes[i] != i:
                    raise ValueError(
                        (
                            "unused category %r in column %r "
                            "(all categories must be used)"
                        )
                        % (category, series.name)
                    )
            assert False  # the for-loop is guaranteed to raise, in theory
    else:
        raise ValueError("unsupported dtype %r in column %r" % (dtype, series.name))


def validate_dataframe(df: pd.DataFrame) -> None:
    """
    Ensure `df` is "valid" as per Workbench standards, or raise ValueError.

    "Valid" means:

    * All column names are str
    * All column names are unique
    * No column names are ""
    * If a column is `object` or `categorical`, all values are `str`, `np.nan`
      or `None`
    * Otherwise, a column must be numeric (but not "nullable integer") or
      datetime (without timezone).
    """
    if df.columns.dtype != object or not (df.columns.map(type) == str).all():
        raise ValueError("column names must all be str")

    if not df.index.equals(pd.RangeIndex(0, len(df))):
        raise ValueError(
            "must use the default RangeIndex — "
            "try table.reset_index(drop=True, inplace=True)"
        )

    dup_column_indexes = df.columns.duplicated()
    if dup_column_indexes.any():
        colname = df.columns[dup_column_indexes][0]
        raise ValueError('duplicate column name "%s"' % colname)

    if (df.columns == "").any():
        raise ValueError('empty column name "" not allowed')

    for column in df.columns:
        validate_series(df[column])
