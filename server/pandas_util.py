from pandas import DataFrame
from pandas.util import hash_pandas_object


def hash_table(table: DataFrame) -> str:
    """Build a hash useful in comparing data frames for equality."""
    h = hash_pandas_object(table).sum()  # xor would be nice, but whatevs
    h = h if h > 0 else -h  # stay positive (sum often overflows)
    return str(h)
