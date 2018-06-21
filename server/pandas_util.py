from pandas import DataFrame
from pandas.util import hash_pandas_object
from typing import Optional

def hash_table(table: DataFrame) -> str:
    """Build a hash useful in comparing data frames for equality."""
    h = hash_pandas_object(table).sum()  # xor would be nice, but whatevs
    h = h if h>0 else -h              # stay positive (sum often overflows)
    return str(h)

def are_tables_equal(df1: Optional[DataFrame],
                     df2: Optional[DataFrame]) -> bool:
    """Compares tables for equality, handling None and empty tables.
    """
    if df1 is None and df2 is None:
        return True
    elif df1 is None or df2 is None:
        return False
    # Now they're both not-None

    if df1.empty != df2.empty:
        return False
    elif df1.empty or df2.empty:
        return True
    # Now they're both non-empty

    if hash_table(df1) != hash_table(df2):
        return False
    # Now they hash to the same number

    return df1.equals(df2) # compare all types and values
