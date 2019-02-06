from enum import Enum
from typing import List
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


class ColumnType(Enum):
    """
    Data type of a column.

    This describes how it is presented -- not how its bytes are arranged. We
    can map from pandas/numpy `dtype` to `ColumnType`, but not vice versa.
    """

    TEXT = 'text'
    NUMBER = 'number'
    DATETIME = 'datetime'

    @classmethod
    def from_dtype(cls, dtype) -> 'ColumnType':
        """
        Determine ColumnType based on pandas/numpy `dtype`.
        """
        if is_numeric_dtype(dtype):
            return ColumnType.NUMBER
        elif is_datetime64_dtype(dtype):
            return ColumnType.DATETIME
        elif dtype == object or dtype == 'category':
            return ColumnType.TEXT
        else:
            raise ValueError(f'Unknown dtype: {dtype}')


class Column:
    """
    A column definition.
    """
    def __init__(self, name: str, type: ColumnType):
        self.name = name
        if not isinstance(type, ColumnType):
            type = ColumnType(type)  # or ValueError
        self.type = type

    def __repr__(self):
        return 'Column' + repr((self.name, self.type))

    def __eq__(self, rhs):
        return (
            isinstance(rhs, Column)
            and (self.name, self.type) == (rhs.name, rhs.type)
        )


class TableShape:
    """
    The rows and columns of a table -- devoid of data.
    """
    def __init__(self, nrows: int, columns: List[Column]):
        self.nrows = nrows
        self.columns = columns

    def __repr__(self):
        return 'TableShape' + repr((self.nrows, self.columns))

    def __eq__(self, rhs):
        return (
            isinstance(rhs, TableShape)
            and (self.nrows, self.columns) == (rhs.nrows, rhs.columns)
        )


class StepResultShape:
    """
    Low-RAM metadata about a ProcessResult.
    """

    def __init__(self, status: str, table_shape: TableShape):
        self.status = status
        self.table_shape = table_shape
