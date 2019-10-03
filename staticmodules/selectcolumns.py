import re
from typing import Tuple
import pandas as pd
from pandas.core.indexes.base import InvalidIndexError


commas = re.compile(r"\s*,\s*")
numbers = re.compile(r"(?P<first>[1-9]\d*)(?:-(?P<last>[1-9]\d*))?")


def select_columns_by_number(table, str_col_nums):
    """
    Return a list of column names, or raise ValueError.
    """
    index = parse_interval_index(str_col_nums)  # raises ValueError

    table_col_nums = list(range(0, len(table.columns)))

    try:
        mask = index.get_indexer(table_col_nums) != -1
    except InvalidIndexError:
        raise ValueError("There are overlapping numbers in input range")

    return list(table.columns[mask])


def parse_interval(s: str) -> Tuple[int, int]:
    """
    Parse a string 'interval' into a tuple
    >>> parse_interval('1')
    (0, 1)
    >>> parse_interval('1-3')
    (0, 2)
    >>> parse_interval('5')
    (4, 4)
    >>> parse_interval('hi')
    Traceback (most recent call last):
        ...
    ValueError: Column numbers must look like "1-2", "5" or "1-2, 5"; got "hi"
    """
    match = numbers.fullmatch(s)
    if not match:
        raise ValueError(
            f'Column numbers must look like "1-2", "5" or "1-2, 5"; got "{s}"'
        )

    first = int(match.group("first"))
    last = int(match.group("last") or first)
    return (first - 1, last - 1)


# See also droprowsbyposition, which inspired this logic.
def parse_interval_index(column_numbers: str) -> pd.IntervalIndex:
    """
    Turn a string like '2,3-5' to a pd.IntervalIndex.

    Return an empty index on empty string.

    Raise ValueError on invalid string.
    """
    tuples = [parse_interval(s) for s in commas.split(column_numbers.strip())]
    return pd.IntervalIndex.from_tuples(tuples, closed="both")


def render(table, params, **kwargs):
    if params["select_range"]:
        try:
            columns = select_columns_by_number(table, params["column_numbers"])
        except ValueError as err:
            return str(err)
    else:
        columns = params["colnames"]

    # if no column has been selected, keep the columns
    if not columns:
        return table

    if not params["keep"]:
        # Invert "columns", maintaining the order from the input table.
        drop_columns = set(columns)
        columns = [c for c in table.columns if c not in drop_columns]

    return table[columns]


def _migrate_params_v0_to_v1(params):
    """
    v0: colnames are comma-separated str; drop_or_keep is 0|1 drop|keep.

    v1: colnames are List[str]; keep is bool.
    """
    return {
        "colnames": [c for c in params["colnames"].split(",") if c],
        "select_range": params["select_range"],
        "column_numbers": params["column_numbers"],
        "keep": params["drop_or_keep"] != 0,
    }


def migrate_params(params):
    if "drop_or_keep" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
