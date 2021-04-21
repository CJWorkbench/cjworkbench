import struct
import unittest
from datetime import date

import pyarrow as pa
from cjwmodule.arrow.testing import make_column

from cjwkernel.types import Column, ColumnType
from cjwkernel.util import tempfile_context
from cjwkernel.validate import (
    read_columns,
    validate_arrow_file,
    DateValueHasWrongUnit,
    DateOutOfRange,
    FieldMetadataNotAllowed,
    InvalidNumberFormat,
    TableSchemaHasMetadata,
    TimestampTimezoneNotAllowed,
    TimestampUnitNotAllowed,
    DuplicateColumnName,
    InvalidArrowFile,
    TableHasTooManyRecordBatches,
    WrongColumnType,
)
from cjwkernel.tests.util import arrow_table_context


def Date(name: str, unit: str) -> Column:
    return Column(name, ColumnType.Date(unit))


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
        with arrow_table_context(make_column("A", ["x"])) as (path, _):
            validate_arrow_file(path)  # do not raise

    def test_arrow_file_does_not_validate(self):
        array = pa.StringArray.from_buffers(
            1,
            # value_offsets: first item spans buffer offsets 0 to 1
            pa.py_buffer(struct.pack("II", 0, 1)),
            # data: a not-UTF8-safe character
            pa.py_buffer(b"\xc9"),
        )
        table = pa.table({"A": array})
        with tempfile_context() as path:
            with pa.ipc.RecordBatchFileWriter(path, table.schema) as writer:
                writer.write_table(table)

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


class ReadColumnsTest(unittest.TestCase):
    def test_table_has_metadata(self):
        table = pa.table({"A": ["x"]}).replace_schema_metadata({})  # non-null
        with self.assertRaises(TableSchemaHasMetadata):
            read_columns(table)

    def test_table_too_many_record_batches(self):
        table = pa.table({"A": pa.chunked_array([pa.array(["x"]), pa.array(["y"])])})
        with self.assertRaises(TableHasTooManyRecordBatches):
            read_columns(table)

    def test_duplicate_column_names(self):
        table = pa.table(
            [pa.array(["x"]), pa.array(["x"])],
            pa.schema([pa.field("A", pa.string()), pa.field("A", pa.string())]),
        )
        with self.assertRaisesRegex(
            DuplicateColumnName,
            "Table has two columns named 'A': column 0 and column 1",
        ):
            read_columns(table)

    def test_timestamp_metadata_non_null(self):
        table = pa.table(
            [pa.array([123123123], pa.timestamp("ns"))],
            pa.schema([pa.field("A", pa.timestamp("ns"), metadata={b"foo": b"bar"})]),
        )
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_timestamp_tz_non_null(self):
        table = pa.table(
            {"A": pa.array([12312312314512], pa.timestamp("ns", tz="utc"))}
        )
        with self.assertRaisesRegex(
            TimestampTimezoneNotAllowed, "Workbench does not support time zones"
        ):
            read_columns(table)

    def test_timestamp_unit_not_ns(self):
        table = pa.table({"A": pa.array([12312312314512], pa.timestamp("us"))})
        with self.assertRaisesRegex(
            TimestampUnitNotAllowed, "Workbench only supports 'ns'"
        ):
            read_columns(table)

    def test_timestamp_ok(self):
        table = pa.table({"A": pa.array([12312312314512], pa.timestamp("ns"))})
        self.assertEqual(read_columns(table), [Column("A", ColumnType.Timestamp())])

    def test_date_metadata_none(self):
        table = pa.table({"A": pa.array([123123123], pa.date32())})
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_date_metadata_too_many_keys(self):
        table = pa.table(
            [pa.array([date(2021, 4, 4)])],
            pa.schema(
                [pa.field("A", pa.date32(), metadata={b"unit": b"day", b"foo": b"bar"})]
            ),
        )
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_date_metadata_invalid_unit(self):
        table = pa.table(
            [pa.array([date(2021, 4, 4)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"days"})]),
        )
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_date_unit_day_ok(self):
        table = pa.table(
            [pa.array([date(2021, 4, 4)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"day"})]),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Date(unit="day"))]
        )

    def test_date_unit_week_bad(self):
        table = pa.table(
            [pa.array([date(2021, 4, 4)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"week"})]),
        )
        with self.assertRaises(DateValueHasWrongUnit):
            read_columns(table)

    def test_date_unit_week_ok(self):
        table = pa.table(
            [pa.array([date(2021, 4, 5), date(2021, 4, 12), None])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"week"})]),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Date(unit="week"))]
        )

    def test_date_unit_month_bad(self):
        table = pa.table(
            [pa.array([date(2021, 4, 2)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"month"})]),
        )
        with self.assertRaises(DateValueHasWrongUnit):
            read_columns(table)

    def test_date_unit_month_ok(self):
        table = pa.table(
            [pa.array([date(1200, 12, 1), date(3199, 2, 1), None])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"month"})]),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Date(unit="month"))]
        )

    def test_date_unit_quarter_bad(self):
        table = pa.table(
            [pa.array([date(2021, 3, 1)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"quarter"})]),
        )
        with self.assertRaises(DateValueHasWrongUnit):
            read_columns(table)

    def test_date_unit_quarter_ok(self):
        table = pa.table(
            [
                pa.array(
                    [
                        date(1900, 1, 1),
                        date(1900, 4, 1),
                        date(1900, 7, 1),
                        date(1900, 10, 1),
                        None,
                    ]
                )
            ],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"quarter"})]),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Date(unit="quarter"))]
        )

    def test_date_unit_year_bad(self):
        table = pa.table(
            [pa.array([date(1900, 4, 1)])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"year"})]),
        )
        with self.assertRaises(DateValueHasWrongUnit):
            read_columns(table)

    def test_date_unit_year_ok(self):
        table = pa.table(
            [pa.array([date(1900, 1, 1), date(1, 1, 1), date(9999, 1, 1), None])],
            pa.schema([pa.field("A", pa.date32(), metadata={b"unit": b"year"})]),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Date(unit="year"))]
        )

    def test_text_metadata_not_none(self):
        table = pa.table(
            [pa.array(["x"])],
            pa.schema([pa.field("A", pa.string(), metadata={b"unit": b"year"})]),
        )
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_text_ok(self):
        self.assertEqual(
            read_columns(pa.table({"A": ["x"]})), [Column("A", ColumnType.Text())]
        )

    def test_text_dictionary_ok(self):
        self.assertEqual(
            read_columns(
                pa.table({"A": pa.array(["x"]).dictionary_encode()}),
            ),
            [Column("A", ColumnType.Text())],
        )

    def test_number_metadata_none(self):
        table = pa.table({"A": pa.array([123123123])})
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_number_metadata_too_many_keys(self):
        table = pa.table(
            [pa.array([123])],
            pa.schema(
                [
                    pa.field(
                        "A", pa.int64(), metadata={b"format": b"{:,}", b"foo": b"bar"}
                    )
                ]
            ),
        )
        with self.assertRaises(FieldMetadataNotAllowed):
            read_columns(table)

    def test_number_metadata_invalid_format(self):
        table = pa.table(
            [pa.array([123])],
            pa.schema([pa.field("A", pa.int64(), metadata={b"format": b"{:,invalid"})]),
        )
        with self.assertRaises(InvalidNumberFormat):
            read_columns(table)

    def test_number_metadata_format_invalid_utf8(self):
        table = pa.table(
            [pa.array([123])],
            pa.schema(
                [pa.field("A", pa.int64(), metadata={b"format": b"\xe2{:,.2f}"})]
            ),
        )
        with self.assertRaises(InvalidNumberFormat):
            read_columns(table)

    def test_number_metadata_utf8_format(self):
        table = pa.table(
            [pa.array([123])],
            pa.schema(
                [
                    pa.field(
                        "A",
                        pa.int64(),
                        metadata={b"format": "€{:,.2f}".encode("utf-8")},
                    )
                ]
            ),
        )
        self.assertEqual(
            read_columns(table), [Column("A", ColumnType.Number(format="€{:,.2f}"))]
        )

    def test_unknown_column_type(self):
        table = pa.table({"A": pa.array([1231231], pa.time64("ns"))})
        with self.assertRaises(WrongColumnType):
            read_columns(table)
