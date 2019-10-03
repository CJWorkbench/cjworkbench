import unittest
import pyarrow
from cjwkernel.types import Column, ColumnType, TableMetadata
from cjwkernel.validate import (
    validate,
    ColumnDataIsInvalidUtf8,
    ColumnNameIsInvalidUtf8,
    DictionaryColumnHasUnusedEntry,
    DatetimeTimezoneNotAllowed,
    DatetimeUnitNotAllowed,
    DuplicateColumnName,
    TableHasTooManyRecordBatches,
    TableShouldBeNone,
    WrongColumnCount,
    WrongColumnName,
    WrongColumnType,
    WrongRowCount,
)


def Text(name: str) -> Column:
    return Column(name, ColumnType.Text())


def Number(name: str, format: str = "{:,.2f}") -> Column:
    return Column(name, ColumnType.Number(format=format))


def Datetime(name: str) -> Column:
    return Column(name, ColumnType.Datetime())


class ValidateTests(unittest.TestCase):
    def test_table_none_when_should_be_set(self):
        with self.assertRaises(WrongColumnCount):
            validate(None, TableMetadata(2, [Text("A")]))

    def test_table_not_none_when_should_be_none(self):
        with self.assertRaises(TableShouldBeNone):
            validate(pyarrow.Table.from_arrays([]), TableMetadata(2, []))

    def test_table_wrong_number_of_rows(self):
        with self.assertRaises(WrongRowCount):
            validate(
                pyarrow.Table.from_pydict({"A": ["x"]}), TableMetadata(2, [Text("A")])
            )

    def test_table_not_one_batch(self):
        with self.assertRaises(TableHasTooManyRecordBatches):
            validate(
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
            validate(
                pyarrow.Table.from_arrays(
                    [pyarrow.array(["a"]), pyarrow.array(["b"])], ["A", "A"]
                ),
                TableMetadata(1, [Text("A"), Text("A")]),
            )

    def test_column_name_mismatch(self):
        with self.assertRaises(WrongColumnName):
            validate(
                pyarrow.table({"A": ["a"], "B": ["b"]}),
                TableMetadata(1, [Text("A"), Text("B2")]),
            )

    def test_column_name_not_utf8(self):
        bad_str = "\ud800x"  # invalid continuation byte
        bad_bytes = b"\xed\xa0\x80x"  # bad_str, encoded to utf-8

        with self.assertRaises(ColumnNameIsInvalidUtf8):
            validate(
                pyarrow.Table.from_arrays([pyarrow.array(["a"])], [bad_bytes]),
                TableMetadata(1, [Text(bad_str)]),
            )

    def test_column_int_should_be_text(self):
        with self.assertRaises(WrongColumnType):
            validate(pyarrow.table({"A": [1]}), TableMetadata(1, [Text("A")]))

    def test_column_str_should_be_number(self):
        with self.assertRaises(WrongColumnType):
            validate(pyarrow.table({"A": ["x"]}), TableMetadata(1, [Number("A")]))

    def test_column_str_should_be_datetime(self):
        with self.assertRaises(WrongColumnType):
            validate(pyarrow.table({"A": ["x"]}), TableMetadata(1, [Datetime("A")]))

    def test_column_datetime_should_be_tz_naive(self):
        with self.assertRaises(DatetimeTimezoneNotAllowed):
            validate(
                pyarrow.table(
                    {
                        "A": pyarrow.array(
                            [5298375234123],
                            type=pyarrow.timestamp("ns", "America/New_York"),
                        )
                    }
                ),
                TableMetadata(1, [Datetime("A")]),
            )

    def test_column_datetime_must_be_ns_resolution(self):
        # [2019-09-17] Pandas only supports datetime64[ns]
        # https://github.com/pandas-dev/pandas/issues/7307#issuecomment-224180563
        with self.assertRaises(DatetimeUnitNotAllowed):
            validate(
                pyarrow.table(
                    {
                        "A": pyarrow.array(
                            [5298375234], type=pyarrow.timestamp("us", tz=None)
                        )
                    }
                ),
                TableMetadata(1, [Datetime("A")]),
            )

    def test_text_zero_chunks_valid(self):
        validate(
            pyarrow.Table.from_batches([], pyarrow.schema([("A", pyarrow.string())])),
            TableMetadata(0, [Text("A")]),
        )

    def test_text_dictionary_zero_chunks_is_valid(self):
        validate(
            pyarrow.Table.from_batches(
                [],
                pyarrow.schema(
                    [("A", pyarrow.dictionary(pyarrow.int32(), pyarrow.string()))]
                ),
            ),
            TableMetadata(0, [Text("A")]),
        )

    def test_text_invalid_utf8(self):
        # Let's construct a particularly tricky case: two strings that are
        # invalid on their own but are valid when concatenated. (In the buffer
        # they're concatenated, so the buffer bytes are valid utf-8 even though
        # the values aren't.)
        #
        # We'll also throw in a NULL, so we don't get tempted to ignore them
        # when we optimize this validation.
        poop_bytes = "💩".encode("utf-8")
        binary_array = pyarrow.array([None, poop_bytes[:2], poop_bytes[2:]])
        _, offsets, data = binary_array.buffers()
        with self.assertRaises(ColumnDataIsInvalidUtf8):
            validate(
                pyarrow.table(
                    {"A": pyarrow.StringArray.from_buffers(3, offsets, data)}
                ),
                TableMetadata(3, [Text("A")]),
            )

    def test_text_invalid_utf8_dictionary(self):
        # Let's construct a particularly tricky case: two strings that are
        # invalid on their own but are valid when concatenated. (In the buffer
        # they're concatenated, so the buffer bytes are valid utf-8 even though
        # the values aren't.)
        #
        # We can't _create_ a pyarrow.Array by passing `pyarrow.array()` bad
        # UTF-8, because `pyarrow.array()` actually encodes UTF-8 to binary.
        # But we _can_ create a table with invalid UTF-8 binary, by writing
        # buffers directly.
        poop_bytes = "💩".encode("utf-8")
        binary_array = pyarrow.array([poop_bytes[:2], poop_bytes[2:]])
        _, offsets, data = binary_array.buffers()
        with self.assertRaises(ColumnDataIsInvalidUtf8):
            validate(
                pyarrow.table(
                    {
                        "A": pyarrow.DictionaryArray.from_arrays(
                            pyarrow.array([0, 1]),
                            pyarrow.StringArray.from_buffers(2, offsets, data),
                        )
                    }
                ),
                TableMetadata(2, [Text("A")]),
            )

    # TODO
    # pyarrow.DictionaryArray.from_arrays() already does this validation.
    # We'd need to use something other than pyarrow to forge this data.
    # def test_dictionary_column_has_invalid_index(self):

    def test_dictionary_column_has_unused_entry(self):
        with self.assertRaises(DictionaryColumnHasUnusedEntry):
            validate(
                pyarrow.table(
                    {
                        "A": pyarrow.array(
                            ["x", None, "y", "y", "z"]
                        ).dictionary_encode()[0:4]
                    }
                ),
                TableMetadata(4, [Text("A")]),
            )

    def test_empty_dictionary_is_valid(self):
        validate(
            pyarrow.table({"A": pyarrow.array(["x"]).dictionary_encode()[0:0]}),
            TableMetadata(0, [Text("A")]),
        )

    def test_happy_path_table_is_none(self):
        validate(None, TableMetadata(2, []))
