import struct
import unittest
import pyarrow
from cjwkernel.types import Column, ColumnType, TableMetadata
from cjwkernel.util import tempfile_context
from cjwkernel.validate import (
    validate_arrow_file,
    validate_table_metadata,
    TimestampTimezoneNotAllowed,
    TimestampUnitNotAllowed,
    DuplicateColumnName,
    InvalidArrowFile,
    TableHasTooManyRecordBatches,
    TableShouldBeNone,
    WrongColumnCount,
    WrongColumnName,
    WrongColumnType,
    WrongRowCount,
)
from cjwkernel.tests.util import arrow_file


def Text(name: str) -> Column:
    return Column(name, ColumnType.Text())


def Number(name: str, format: str = "{:,.2f}") -> Column:
    return Column(name, ColumnType.Number(format=format))


def Timestamp(name: str) -> Column:
    return Column(name, ColumnType.Timestamp())


class ValidateArrowFileTests(unittest.TestCase):
    # A note on implementation: we know validate_arrow_file() simply runs
    # /usr/bin/arrow-validate. We aren't testing /usr/bin/arrow-validate here.
    # We're just testing that errors get propagated and success is possible.

    def test_happy_path(self):
        with arrow_file({"A": [1, 2, 3]}) as path:
            validate_arrow_file(path)  # do not raise

    def test_arrow_file_does_not_validate(self):
        array = pyarrow.StringArray.from_buffers(
            1,
            # value_offsets: first item spans buffer offsets 0 to 1
            pyarrow.py_buffer(struct.pack("II", 0, 1)),
            # data: a not-UTF8-safe character
            pyarrow.py_buffer(b"\xc9"),
        )
        with arrow_file({"A": array}) as path:
            with self.assertRaisesRegex(
                InvalidArrowFile, "arrow-validate: --check-safe failed"
            ):
                validate_arrow_file(path)

    def test_arrow_file_does_not_open(self):
        with tempfile_context() as path:
            path.write_bytes(b"this is not an Arrow file")
            with self.assertRaisesRegex(
                InvalidArrowFile, "arrow-validate: .*Not an Arrow file"
            ):
                validate_arrow_file(path)

    def test_arrow_file_does_not_exist(self):
        with tempfile_context() as path:
            path.unlink()
            with self.assertRaisesRegex(
                InvalidArrowFile, "arrow-validate: .*No such file or directory"
            ):
                validate_arrow_file(path)


class ValidateTableMetadataTests(unittest.TestCase):
    def test_table_none_when_should_be_set(self):
        with self.assertRaises(WrongColumnCount):
            validate_table_metadata(None, TableMetadata(2, [Text("A")]))

    def test_table_not_none_when_should_be_none(self):
        with self.assertRaises(TableShouldBeNone):
            validate_table_metadata(pyarrow.Table.from_arrays([]), TableMetadata(2, []))

    def test_table_wrong_number_of_rows(self):
        with self.assertRaises(WrongRowCount):
            validate_table_metadata(
                pyarrow.Table.from_pydict({"A": ["x"]}), TableMetadata(2, [Text("A")])
            )

    def test_table_not_one_batch(self):
        with self.assertRaises(TableHasTooManyRecordBatches):
            validate_table_metadata(
                pyarrow.Table.from_batches(
                    [
                        pyarrow.RecordBatch.from_arrays([pyarrow.array(["a"])], ["A"]),
                        pyarrow.RecordBatch.from_arrays([pyarrow.array(["b"])], ["A"]),
                    ]
                ),
                TableMetadata(2, [Text("A")]),
            )

    def test_duplicate_column_name(self):
        with self.assertRaises(DuplicateColumnName):
            validate_table_metadata(
                pyarrow.Table.from_arrays(
                    [pyarrow.array(["a"]), pyarrow.array(["b"])], ["A", "A"]
                ),
                TableMetadata(1, [Text("A"), Text("A")]),
            )

    def test_column_name_mismatch(self):
        with self.assertRaises(WrongColumnName):
            validate_table_metadata(
                pyarrow.table({"A": ["a"], "B": ["b"]}),
                TableMetadata(1, [Text("A"), Text("B2")]),
            )

    def test_column_int_should_be_text(self):
        with self.assertRaises(WrongColumnType):
            validate_table_metadata(
                pyarrow.table({"A": [1]}), TableMetadata(1, [Text("A")])
            )

    def test_column_str_should_be_number(self):
        with self.assertRaises(WrongColumnType):
            validate_table_metadata(
                pyarrow.table({"A": ["x"]}), TableMetadata(1, [Number("A")])
            )

    def test_column_str_should_be_timestamp(self):
        with self.assertRaises(WrongColumnType):
            validate_table_metadata(
                pyarrow.table({"A": ["x"]}), TableMetadata(1, [Timestamp("A")])
            )

    def test_column_timestamp_should_be_tz_naive(self):
        with self.assertRaises(TimestampTimezoneNotAllowed):
            validate_table_metadata(
                pyarrow.table(
                    {
                        "A": pyarrow.array(
                            [5298375234123],
                            type=pyarrow.timestamp("ns", "America/New_York"),
                        )
                    }
                ),
                TableMetadata(1, [Timestamp("A")]),
            )

    def test_column_timestamp_must_be_ns_resolution(self):
        # [2019-09-17] Pandas only supports datetime64[ns]
        # https://github.com/pandas-dev/pandas/issues/7307#issuecomment-224180563
        with self.assertRaises(TimestampUnitNotAllowed):
            validate_table_metadata(
                pyarrow.table(
                    {
                        "A": pyarrow.array(
                            [5298375234], type=pyarrow.timestamp("us", tz=None)
                        )
                    }
                ),
                TableMetadata(1, [Timestamp("A")]),
            )

    def test_text_zero_chunks_valid(self):
        validate_table_metadata(
            pyarrow.Table.from_batches([], pyarrow.schema([("A", pyarrow.string())])),
            TableMetadata(0, [Text("A")]),
        )

    def test_text_dictionary_zero_chunks_is_valid(self):
        validate_table_metadata(
            pyarrow.Table.from_batches(
                [],
                pyarrow.schema(
                    [("A", pyarrow.dictionary(pyarrow.int32(), pyarrow.string()))]
                ),
            ),
            TableMetadata(0, [Text("A")]),
        )

    def test_happy_path_table_is_none(self):
        validate_table_metadata(None, TableMetadata(2, []))
