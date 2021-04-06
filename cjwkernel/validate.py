import datetime
import subprocess
import time
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.compute

from .types import ColumnType, TableMetadata
from . import settings


class ValidateError(ValueError):
    """Arrow table and metadata do not meet Workbench's requirements."""


class InvalidArrowFile(ValidateError):
    """arrow-validate of a path failed.

    Run arrow-validate before opening an Arrow file in Python, for SECURITY.
    """

    def __init__(self, text):
        super().__init__("arrow-validate: " + text)


class TableShouldBeNone(ValidateError):
    def __init__(self):
        super().__init__(
            "Table must be None because metadata says there are no columns"
        )


class TableHasTooManyRecordBatches(ValidateError):
    def __init__(self, actual: int):
        super().__init__("Table has %d record batches; we only support 1" % actual)


class WrongColumnName(ValidateError):
    def __init__(self, position: int, expected: str, actual: str):
        super().__init__(
            "Table column %d has wrong name: metadata says '%s', table says '%s'"
            % (position, expected, actual)
        )


class DuplicateColumnName(ValidateError):
    def __init__(self, name: str, position1: int, position2: int):
        super().__init__(
            "Table has two columns named '%s': column %d and column %d"
            % (name, position1, position2)
        )


class WrongColumnType(ValidateError):
    def __init__(self, name: str, expected: ColumnType, actual: pa.DataType):
        super().__init__(
            "Table column '%s' has wrong type: expected %r, got %r"
            % (name, expected, actual)
        )


class TimestampTimezoneNotAllowed(ValidateError):
    def __init__(self, name: str, dtype: pa.TimestampType):
        super().__init__(
            "Table column '%s' (%r) has a time zone, but Workbench does not support time zones"
            % (name, dtype)
        )


class TimestampUnitNotAllowed(ValidateError):
    def __init__(self, name: str, dtype: pa.TimestampType):
        super().__init__(
            "Table column '%s' (%r) has unit '%s', but Workbench only supports 'ns'"
            % (name, dtype, dtype.unit)
        )


class DateOutOfRange(ValidateError):
    def __init__(self, name: str):
        super().__init__(
            "Table column %r has invalid value(s): the valid range is 0001-01-01 - 9999-12-31."
            % (name,)
        )


class DateValueHasWrongUnit(ValidateError):
    def __init__(self, name: str, unit: str):
        super().__init__(
            "Table column %r has invalid value: every date must be the first day of a %r"
            % (name, unit)
        )


class WrongColumnCount(ValidateError):
    def __init__(self, expect: int, actual: int):
        super().__init__(
            "Table has wrong column count (metadata says %d, table has %d)"
            % (expect, actual)
        )


class WrongRowCount(ValidateError):
    def __init__(self, expect: int, actual: int):
        super().__init__(
            "Table has wrong row count (metadata says %d, table has %d)"
            % (expect, actual)
        )


def validate_arrow_file(path: Path) -> None:
    """Validate that `table` can be loaded at all.

    Raise InvalidArrowFile if:

    * The file is empty or has no Arrow header
    * Text columns' offsets are invalid
    * A column name has invalid UTF-8
    * A column name is too long (see settings.MAX_BYTES_PER_COLUMN_NAME)
    * A column name contains ASCII control characters (a newline, for example)
    * Some text data has invalid UTF-8
    * A float is NaN or Infinity.
    * A dictionary column's dictionary contains nulls or unused values
    """
    try:
        subprocess.run(
            [
                "/usr/bin/arrow-validate",
                "--check-column-name-control-characters",
                f"--check-column-name-max-bytes={settings.MAX_BYTES_PER_COLUMN_NAME}",
                "--check-dictionary-values-all-used",
                "--check-dictionary-values-not-null",
                "--check-dictionary-values-unique",
                "--check-floats-all-finite",
                "--check-safe",
                path.as_posix(),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as err:
        message = err.stdout[:-1]  # strip trailing "\n"
        raise InvalidArrowFile(message) from None


def validate_table_metadata(table: Optional[pa.Table], metadata: TableMetadata) -> None:
    """Validate that `table` matches `metadata` and Workbench's assumptions.

    Raise ValidateError if:

    * `table is not None` and `metadata.columns` is empty
    * `table is None` and `metadata.columns` is not empty
    * table has more than one record batch
    * table and metadata have different numbers of columns or rows
    * table column names do not match metadata column names
    * table column names have duplicates
    * table column types are not compatible with metadata column types
      (e.g., Numbers column in metadata, Timestamp table type)
    * table values do not agree with metadata column types
      (e.g., Date32 5th of the month with metadata-type "Date:month")

    Be sure the Arrow file backing the table was validated with
    `validate_arrow_file()` first. Otherwise, you may experience a
    UnicodeError while printing error messages, or subsequent code may
    read memory outside the Arrow file.
    """
    if table is None:
        if metadata.columns:
            raise WrongColumnCount(0, len(metadata.columns))
    else:
        if not metadata.columns:
            raise TableShouldBeNone

        if metadata.n_rows != table.num_rows:
            raise WrongRowCount(metadata.n_rows, table.num_rows)
        seen_column_names = {}
        for position, expected in enumerate(metadata.columns):
            actual = table.column(position)
            actual_name = actual._name
            if position == 0 and actual.num_chunks > 1:
                raise TableHasTooManyRecordBatches(actual.num_chunks)
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
                    pa.types.is_string(actual.type)
                    or (
                        pa.types.is_dictionary(actual.type)
                        and pa.types.is_string(actual.type.value_type)
                    )
                ):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
            elif isinstance(expected.type, ColumnType.Number):
                if not (
                    pa.types.is_floating(actual.type)
                    or pa.types.is_integer(actual.type)
                ):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
            elif isinstance(expected.type, ColumnType.Timestamp):
                if not pa.types.is_timestamp(actual.type):
                    raise WrongColumnType(actual_name, expected.type, actual.type)
                if actual.type.tz is not None:
                    raise TimestampTimezoneNotAllowed(actual_name, actual.type)
                if actual.type.unit != "ns":
                    raise TimestampUnitNotAllowed(actual_name, actual.type)
            elif isinstance(expected.type, ColumnType.Date):
                if not pa.types.is_date32(actual.type):
                    raise WrongColumnType(actual_name, expected.type, actual.type)

                if expected.type.unit == "day":
                    pass  # all int32 are valid
                elif expected.type.unit == "week":
                    # Only Mondays (ISO weekday = 0) are valid
                    for chunk in actual.chunks:
                        # 1970-01-01 (date32=0) was Thursday. Shift such that
                        # date32=0 is Monday. If chunk == -3, monday0_i64 == 0.
                        #
                        # We use i64 to avoid overflow
                        monday0_i64 = pa.compute.add(
                            chunk.view(pa.int32()).cast(pa.int64()), 3
                        )
                        # divide+multiply. For each date in monday0_i64,
                        # all_mondays will be the monday of that week
                        all_mondays = pa.compute.multiply(
                            pa.compute.divide(monday0_i64, 7), 7
                        )
                        if pa.compute.any(
                            pa.compute.not_equal(monday0_i64, all_mondays)
                        ).as_py():
                            raise DateValueHasWrongUnit(actual_name, "week")
                else:
                    is_valid = {
                        "month": lambda st: st.tm_mday == 1,
                        "quarter": lambda st: st.tm_mday == 1 and st.tm_mon % 3 == 1,
                        "year": lambda st: st.tm_mon == 1 and st.tm_mday == 1,
                    }[expected.type.unit]
                    for chunk in actual.chunks:
                        unix_timestamps = pa.compute.multiply(
                            chunk.view(pa.int32()).cast(pa.int64()), 86400
                        )
                        for unix_timestamp in unix_timestamps:
                            if unix_timestamp.is_valid:
                                struct_time = time.gmtime(unix_timestamp.as_py())
                                if not is_valid(struct_time):
                                    raise DateValueHasWrongUnit(
                                        actual_name, expected.type.unit
                                    )

            else:
                raise NotImplementedError
