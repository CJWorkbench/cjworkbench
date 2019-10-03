from typing import Optional
import numpy as np
import pyarrow
from .types import ColumnType, TableMetadata


class ValidateError(ValueError):
    """
    Arrow table and metadata do not meet Workbench's requirements.
    """


class TableShouldBeNone(ValueError):
    def __init__(self):
        super().__init__(
            "Table must be None because metadata says there are no columns"
        )


class TableHasTooManyRecordBatches(ValueError):
    def __init__(self, actual: int):
        super().__init__("Table has %d record batches; we only support 1" % actual)


class WrongColumnName(ValueError):
    def __init__(self, position: int, expected: str, actual: str):
        super().__init__(
            "Table column %d has wrong name: metadata says '%s', table says '%s'"
            % (position, expected, actual)
        )


class DuplicateColumnName(ValueError):
    def __init__(self, name: str, position1: int, position2: int):
        super().__init__(
            "Table has two columns named '%s': column %d and column %d"
            % (name, position1, position2)
        )


class ColumnNameIsInvalidUtf8(ValueError):
    def __init__(self, position: int):
        super().__init__("Table column %d has invalid UTF-8 name" % (position,))


class ColumnDataIsInvalidUtf8(ValueError):
    def __init__(self, column: str, row: int):
        super().__init__(
            "Table column '%s' has invalid UTF-8 data on row %d" % (column, row)
        )


class DictionaryColumnHasUnusedEntry(ValueError):
    def __init__(self, column: str, entry: str):
        super().__init__(
            "Table column '%s' has unused dictionary entry '%s'" % (column, entry)
        )


class DictionaryColumnHasInvalidIndex(ValueError):
    def __init__(self, column: str, row: int, index: int):
        super().__Init__(
            "Table column '%s' has invalid dictionary index %d at row %d"
            % (column, index, row)
        )


class WrongColumnType(ValueError):
    def __init__(self, name: str, expected: ColumnType, actual: pyarrow.DataType):
        super().__init__(
            "Table column '%s' has wrong type: expected %r, got %r"
            % (name, expected, actual)
        )


class DatetimeTimezoneNotAllowed(ValueError):
    def __init__(self, name: str, dtype: pyarrow.TimestampType):
        super().__init__(
            "Table column '%s' (%r) has a time zone, but Workbench does not support time zones"
            % (name, dtype)
        )


class DatetimeUnitNotAllowed(ValueError):
    def __init__(self, name: str, dtype: pyarrow.TimestampType):
        super().__init__(
            "Table column '%s' (%r) has unit '%s', but Workbench only supports 'ns'"
            % (name, dtype, dtype.unit)
        )


class WrongColumnCount(ValueError):
    def __init__(self, expect: int, actual: int):
        super().__init__(
            "Table has wrong column count (metadata says %d, table has %d)"
            % (expect, actual)
        )


class WrongRowCount(ValueError):
    def __init__(self, expect: int, actual: int):
        super().__init__(
            "Table has wrong row count (metadata says %d, table has %d)"
            % (expect, actual)
        )


def _validate_strings_are_utf8(array: pyarrow.StringArray, column_name: str) -> None:
    try:
        for row, value in enumerate(array):
            value.as_py()  # decode utf-8
    except UnicodeDecodeError:
        raise ColumnDataIsInvalidUtf8(column_name, row)


def validate(table: Optional[pyarrow.Table], metadata: TableMetadata) -> None:
    """
    Validate that `table` matches `metadata` and Workbench's assumptions.

    Raise ValueError if:

    * `table is not None` and `metadata.columns` is empty
    * `table is None` and `metadata.columns` is not empty
    * table has more than one record batch
    * table and metadata have different numbers of columns or rows
    * table column names do not match metadata column names
    * table column names have duplicates
    * table column names are not valid UTF-8
    * table column types are not compatible with metadata column types
      (e.g., Numbers column in metadata, Datetime table type)
    - table text values are not valid UTF-8
    - dictionary has unused entries
    """
    if table is None:
        if metadata.columns:
            raise WrongColumnCount(0, len(metadata.columns))
    else:
        if not metadata.columns:
            raise TableShouldBeNone
        if table.columns[0].data.num_chunks > 1:
            raise TableHasTooManyRecordBatches(table.columns[0].data.num_chunks)
        if metadata.n_rows != table.num_rows:
            raise WrongRowCount(metadata.n_rows, table.num_rows)
        seen_column_names = {}
        for position, expected, actual in zip(
            range(len(metadata.columns)), metadata.columns, table.columns
        ):
            try:
                # actual stores names as bytes, not str. The `.name` getter
                # forces decoding.
                actual_name = actual.name
            except UnicodeDecodeError:
                raise ColumnNameIsInvalidUtf8(position)
            if expected.name != actual_name:
                raise WrongColumnName(position, expected.name, actual_name)
            if actual_name in seen_column_names:
                raise DuplicateColumnName(
                    actual_name, seen_column_names[actual_name], position
                )
            else:
                seen_column_names[actual_name] = position

            if isinstance(expected.type, ColumnType.Text):
                if not (
                    pyarrow.types.is_string(actual.type)
                    or (
                        pyarrow.types.is_dictionary(actual.type)
                        and pyarrow.types.is_string(actual.type.value_type)
                    )
                ):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
                # Validate string values are UTF-8
                for i, chunk in enumerate(actual.data.chunks):
                    if pyarrow.types.is_string(chunk.type):
                        _validate_strings_are_utf8(chunk, actual_name)
                    else:
                        dictionary = chunk.dictionary
                        _validate_strings_are_utf8(dictionary, actual_name)
                        # Now check that all indices are used and valid.
                        # We want this check, which is why we raise
                        # TableHasTooManyRecordBatches
                        used_indices = np.zeros(len(dictionary), dtype=np.bool)
                        try:
                            for row, dict_index in enumerate(chunk.indices):
                                if dict_index is not pyarrow.NULL:
                                    used_indices[dict_index.as_py()] = True
                        except IndexError:
                            raise DictionaryColumnHasInvalidIndex(
                                actual.name, row, dict_index
                            )
                        # np.where() gives tuple of arrays, one for each axis
                        unused_indices = np.where(~used_indices)[0]
                        if unused_indices:
                            raise DictionaryColumnHasUnusedEntry(
                                actual.name, dictionary[unused_indices[0]]
                            )
            elif isinstance(expected.type, ColumnType.Number):
                if not (
                    pyarrow.types.is_floating(actual.type)
                    or pyarrow.types.is_integer(actual.type)
                ):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
            elif isinstance(expected.type, ColumnType.Datetime):
                if not pyarrow.types.is_timestamp(actual.type):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
                if actual.type.tz is not None:
                    raise DatetimeTimezoneNotAllowed(actual_name, actual.type)
                if actual.type.unit != "ns":
                    raise DatetimeUnitNotAllowed(actual_name, actual.type)
            else:
                raise NotImplementedError
