import re
from typing import Tuple
from pandas import IntervalIndex
from .utils import parse_multicolumn_param


commas = re.compile(r'\s*,\s*')
numbers = re.compile(r'(?P<first>[1-9]\d*)(?:-(?P<last>[1-9]\d*))?')


Drop = 0
Keep = 1


def select_columns_by_name(table, cols, drop_or_keep):
    # if no column has been selected, keep the columns
    if not cols:
        return table

    # ensure we do not change the order of the columns, even if they are
    # listed in another order this also silently removes any nonexistent
    # columns (can happen when re-ordering module, etc.)
    newcols = table.columns.intersection(set(cols))

    if drop_or_keep == Keep:
        table2 = table[newcols]
    else:
        table2 = table.drop(newcols, axis=1)
    return table2


def select_columns_by_number(table, str_col_nums, drop_or_keep):
    try:
        form = Form.parse(str_col_nums)
        if not form:
            return table
    except ValueError as err:
        return str(err)

    table_col_nums = list(range(0, len(table.columns)))

    try:
        mask = form.index.get_indexer(table_col_nums) != -1
    except KeyError:
        return 'There are overlapping numbers in input range'
    except Exception as err:  # TODO huh? What exceptions?
        return str(err.args[0])

    if drop_or_keep == Drop:
        new_col_nums = [x[0] for x in enumerate(mask) if not x[1]]
    else:
        new_col_nums = [x[0] for x in enumerate(mask) if x[1]]
    ret = table.iloc[:, new_col_nums]
    return ret


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
    ValueError: Rows must look like "1-2", "5" or "1-2, 5"; got "hi"
    """
    match = numbers.fullmatch(s)
    if not match:
        raise ValueError(
            f'Rows must look like "1-2", "5" or "1-2, 5"; got "{s}"'
        )

    first = int(match.group('first'))
    last = int(match.group('last') or first)
    return (first - 1, last - 1)


# Copied from droprowsbyposition.py and modified for columns
class Form:
    def __init__(self, index: IntervalIndex):
        self.index = index

    @staticmethod
    def parse_v1(column_numbers: str) -> 'Form':
        """Parse 'column_numbers', or raise ValueError"""
        tuples = [parse_interval(s)
                  for s in commas.split(column_numbers.strip())]
        return Form(IntervalIndex.from_tuples(tuples, closed='both'))

    @staticmethod
    def parse(str_col_nums: str) -> 'Form':
        try:
            if not str_col_nums:
                return None
            return Form.parse_v1(str_col_nums)
        except KeyError:
            return None


def render(table, params, **kwargs):
    drop_or_keep: int = params['drop_or_keep']
    select_range: bool = params['select_range']

    if not select_range:
        cols, _ = parse_multicolumn_param(params['colnames'], table)
        return select_columns_by_name(table, cols, drop_or_keep)

    else:
        str_col_nums: str = params['column_numbers']
        return select_columns_by_number(table, str_col_nums, drop_or_keep)
