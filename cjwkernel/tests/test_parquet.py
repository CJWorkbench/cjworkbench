from datetime import datetime
from pathlib import Path
import math
import unittest
import numpy as np
import pyarrow as pa
from cjwkernel import parquet
from cjwkernel.tests.util import arrow_table, assert_arrow_table_equals, parquet_file
from cjwkernel.util import create_tempfile, tempfile_context


class MagicNumbersTest(unittest.TestCase):
    def test_parquet_file_has_magic_numbers(self):
        with parquet_file({"A": [1]}) as path:
            self.assertTrue(parquet.file_has_parquet_magic_number(path))

    def test_empty_file(self):
        with tempfile_context() as path:
            self.assertFalse(parquet.file_has_parquet_magic_number(path))

    def test_very_short_file(self):
        with tempfile_context() as path:
            path.write_bytes(b"PAR")
            self.assertFalse(parquet.file_has_parquet_magic_number(path))

    def test_good_magic_numbers_but_too_short_to_be_parquet(self):
        # Parquet has PAR1 at the beginning and end. But the file "PAR1" on its
        # own is not a Parquet file.
        with tempfile_context() as path:
            path.write_bytes(b"PAR1")
            self.assertFalse(parquet.file_has_parquet_magic_number(path))

    def test_empty_parquet_file(self):
        with parquet_file({}) as path:
            self.assertTrue(parquet.file_has_parquet_magic_number(path))


class ParquetTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp_path = create_tempfile(prefix="parquet-text")

    def tearDown(self):
        self.temp_path.unlink()
        super().tearDown()

    def _testPath(self, relpath):
        return Path(__file__).parent / "test_data" / relpath

    def test_read_issue_361(self):
        # https://github.com/dask/fastparquet/issues/361
        # IndexError loading zero-column dataframe
        assert_arrow_table_equals(
            parquet.read(self._testPath("fastparquet-issue-361.par")), {}
        )

    def test_read_issue_375_uncompressed(self):
        # https://github.com/dask/fastparquet/issues/375
        # large dictionary written by pyarrow.parquet.
        assert_arrow_table_equals(
            parquet.read(self._testPath("fastparquet-issue-375.par")),
            {
                "A": ["A" * 32755] * 10,
                "__index_level_0__": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            },
        )

    def test_read_issue_375_snappy(self):
        assert_arrow_table_equals(
            parquet.read(self._testPath("fastparquet-issue-375-snappy.par")),
            {
                "A": ["A" * 32760] * 10,
                "__index_level_0__": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            },
        )

    def _test_read_write_table(self, table, expected=None):
        table = arrow_table(table).table
        if expected is None:
            expected = table
        else:
            expected = arrow_table(expected).table
        parquet.write(self.temp_path, table)
        result = parquet.read(self.temp_path)
        assert_arrow_table_equals(result, table)

    def test_read_write_int64(self):
        self._test_read_write_table(arrow_table({"A": [1, 2 ** 62, 3]}).table)

    def test_read_write_float64(self):
        self._test_read_write_table(
            {"A": [1.0, 2.2, 3.0, None]}, {"A": [1.0, 2.2, 3.0, None]}
        )

    def test_read_write_float64_all_null(self):
        self._test_read_write_table({"A": pa.array([None], pa.float64())})

    def test_read_write_text(self):
        self._test_read_write_table({"A": ["x", None, "y"]})

    def test_read_write_text_all_null(self):
        self._test_read_write_table({"A": pa.array([None], pa.string())})

    def test_read_write_text_categorical(self):
        table = pa.table({"A": pa.array(["x", None, "y", "x"]).dictionary_encode()})
        self._test_read_write_table(table)

    def test_read_write_datetime(self):
        self._test_read_write_table(
            {"A": pa.array([datetime.now(), None, datetime.now()], pa.timestamp("ns"))}
        )

    def test_na_only_categorical_has_object_dtype(self):
        # Start with a Categorical with no values. (In Workbench, all
        # Categoricals are text.)
        table = pa.table({"A": pa.array([None], pa.string()).dictionary_encode()})
        self._test_read_write_table(table)

    def test_empty_categorical_has_object_dtype(self):
        table = pa.table(
            {
                "A": pa.DictionaryArray.from_arrays(
                    pa.array([], pa.int32()), pa.array([], pa.string())
                )
            }
        )
        self._test_read_write_table(table)

    def test_read_zero_row_group_categorical_has_object_dtype(self):
        # When no row groups are in the file, there actually isn't anything in
        # the file that suggests a dictionary. We should read that empty column
        # back as strings.

        # In this example, `pyarrow.string()` is equivalent to
        # `pyarrow.dictionary(pyarrow.int32(), pyarrow.string())`
        table = pa.Table.from_batches([], schema=pa.schema([("A", pa.string())]))
        self._test_read_write_table(table)


class ReadSliceAsText(unittest.TestCase):
    def test_slice_zero_row_groups(self):
        table = pa.Table.from_batches([], schema=pa.schema([("A", pa.string())]))
        with parquet_file(table) as path:
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(1), range(0)), "A"
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "json", range(1), range(0)), "[]"
            )

    def test_slice_zero_rows(self):
        with tempfile_context() as path:
            # ensure at least 1 row group
            parquet.write(
                path,
                pa.table(
                    {
                        "A": pa.array([], pa.string()),
                        "B": pa.DictionaryArray.from_arrays(
                            pa.array([], pa.int32()), pa.array([], pa.string())
                        ),
                        "C": pa.array([], pa.timestamp("ns")),
                        "D": pa.array([], pa.float64()),
                    }
                ),
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(4), range(0)), "A,B,C,D"
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "json", range(4), range(0)), "[]"
            )

    def test_slice_lots_of_types(self):
        dt1 = datetime(2019, 12, 18, 23, 33, 55, 123000)
        dt2 = datetime(2019, 12, 18)
        with parquet_file(
            {
                "str": ["x", "y", None, ""],
                "cat": pa.array(["x", "y", None, ""]).dictionary_encode(),
                "dt": pa.array([dt1, None, dt2, None], pa.timestamp("ns")),
                "int32": [1, 2, None, 2 ** 31],
                "float": [1.1, None, 3.3, 4.4],
            }
        ) as path:
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(5), range(4)),
                "\n".join(
                    [
                        "str,cat,dt,int32,float",
                        "x,x,2019-12-18T23:33:55.123Z,1,1.1",
                        "y,y,,2,",
                        ",,2019-12-18,,3.3",
                        ",,,2147483648,4.4",
                    ]
                ),
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "json", range(5), range(4)),
                "".join(
                    [
                        "[",
                        '{"str":"x","cat":"x","dt":"2019-12-18T23:33:55.123Z","int32":1,"float":1.1},',
                        '{"str":"y","cat":"y","dt":null,"int32":2,"float":null},',
                        '{"str":null,"cat":null,"dt":"2019-12-18","int32":null,"float":3.3},',
                        '{"str":"","cat":"","dt":null,"int32":2147483648,"float":4.4}',
                        "]",
                    ]
                ),
            )

    def test_slice_ignore_missing_columns(self):
        with parquet_file({"A": [1]}) as path:
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(3), range(1)), "A\n1"
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "json", range(3), range(1)),
                '[{"A":1}]',
            )

    def test_slice_rows(self):
        with parquet_file({"A": [0, 1, 2, 3, 4, 5, 6, 7]}) as path:
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(1), range(2, 5)),
                "A\n2\n3\n4",
            )
            self.assertEqual(
                parquet.read_slice_as_text(path, "json", range(1), range(2, 5)),
                '[{"A":2},{"A":3},{"A":4}]',
            )

    def test_slice_ignore_missing_rows(self):
        with parquet_file({"A": [0, 1, 2, 3]}) as path:
            self.assertEqual(
                parquet.read_slice_as_text(path, "csv", range(1), range(2, 5)),
                "A\n2\n3",
            )
