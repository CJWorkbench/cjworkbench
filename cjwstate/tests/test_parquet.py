from datetime import datetime
from pathlib import Path
import math
import tempfile
from typing import Any, Dict, List
import unittest
import numpy as np
import pyarrow
from cjwkernel.tests.util import arrow_table, assert_arrow_table_equals, parquet_file
from cjwkernel.util import tempfile_context
from cjwstate import parquet


class ParquetTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.temp_file = tempfile.NamedTemporaryFile()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        self.temp_file.close()
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

    def _test_read_write_table(self, table):
        parquet.write(self.temp_path, arrow_table(table).table)
        result = parquet.read(self.temp_path)
        assert_arrow_table_equals(result, table)

    def test_read_write_int64(self):
        self._test_read_write_table(arrow_table({"A": [1, 2 ** 62, 3]}).table)

    def test_read_write_float64(self):
        self._test_read_write_table({"A": [1.0, 2.2, 3.0, np.nan]})

    def test_read_write_float64_all_null(self):
        self._test_read_write_table(
            {"A": pyarrow.array([None], type=pyarrow.float64())}
        )

    def test_read_write_text(self):
        self._test_read_write_table({"A": ["x", None, "y"]})

    def test_read_write_text_all_null(self):
        self._test_read_write_table({"A": pyarrow.array([None], type=pyarrow.string())})

    def test_read_write_text_categorical(self):
        table = pyarrow.table(
            {"A": pyarrow.array(["x", None, "y", "x"]).dictionary_encode()}
        )
        self._test_read_write_table(table)

    def test_read_write_datetime(self):
        self._test_read_write_table({"A": [datetime.now(), None, datetime.now()]})

    def test_na_only_categorical_has_object_dtype(self):
        # Start with a Categorical with no values. (In Workbench, all
        # Categoricals are text.)
        table = pyarrow.table(
            {"A": pyarrow.array([None], type=pyarrow.string()).dictionary_encode()}
        )
        self._test_read_write_table(table)

    def test_empty_categorical_has_object_dtype(self):
        table = pyarrow.table(
            {
                "A": pyarrow.DictionaryArray.from_arrays(
                    pyarrow.array([], type=pyarrow.int32()),
                    pyarrow.array([], type=pyarrow.string()),
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
        table = pyarrow.Table.from_batches(
            [], schema=pyarrow.schema([("A", pyarrow.string())])
        )
        self._test_read_write_table(table)


class ReadPydictTests(unittest.TestCase):
    def test_pydict_zero_row_groups(self):
        table = pyarrow.Table.from_batches(
            [], schema=pyarrow.schema([("A", pyarrow.string())])
        )
        with parquet_file(table) as path:
            self.assertEqual(parquet.read_pydict(path, ["A"], range(0)), {"A": []})

    def test_pydict_zero_rows(self):
        with tempfile_context() as path:
            # ensure at least 1 row group
            parquet.write(
                path,
                pyarrow.table(
                    {
                        "A": pyarrow.array([], type=pyarrow.string()),
                        "B": pyarrow.DictionaryArray.from_arrays(
                            pyarrow.array([], type=pyarrow.int32()),
                            pyarrow.array([], type=pyarrow.string()),
                        ),
                        "C": pyarrow.array([], type=pyarrow.timestamp("ns")),
                        "D": pyarrow.array([], type=pyarrow.float64()),
                    }
                ),
            )
            self.assertEqual(
                parquet.read_pydict(path, ["A", "B", "C", "D"], range(0)),
                {"A": [], "B": [], "C": [], "D": []},
            )

    def test_pydict_lots_of_types(self):
        dt1 = datetime.now()
        dt2 = datetime.now()
        with parquet_file(
            {
                "str": ["x", "y", None, "z"],
                "cat": pyarrow.array(["x", "y", None, "x"]).dictionary_encode(),
                "dt": [dt1, None, dt2, None],
                "int32": [1, 2, 3, 2 ** 31],
                "float": [1.1, 2.2, 3.3, 4.4],
            }
        ) as path:
            self.assertEqual(
                parquet.read_pydict(
                    path, ["str", "cat", "dt", "int32", "int+null", "float"], range(4)
                ),
                {
                    "str": ["x", "y", None, "z"],
                    "cat": ["x", "y", None, "x"],
                    "dt": [dt1, None, dt2, None],
                    "int32": [1, 2, 3, 2 ** 31],
                    "float": [1.1, 2.2, 3.3, 4.4],
                },
            )

    def test_pydict_order_columns_in_table_order(self):
        with parquet_file({"D": [1], "C": [2], "B": [3]}) as path:
            self.assertEqual(
                list(parquet.read_pydict(path, ["B", "C", "D"], range(1)).keys()),
                ["D", "C", "B"],
            )

    def test_pydict_nan(self):
        with parquet_file(
            {"A": pyarrow.array([1.1, float("nan")], type=pyarrow.float64())}
        ) as path:
            result = parquet.read_pydict(path, ["A"], range(2))
            self.assertEqual(result["A"][0], 1.1)
            self.assert_(math.isnan(result["A"][1]))

    def test_pydict_ignore_missing_columns(self):
        with parquet_file({"A": [1]}) as path:
            self.assertEqual(
                parquet.read_pydict(path, ["A", "B", "C"], range(1)), {"A": [1]}
            )

    def test_pydict_only_rows(self):
        with parquet_file({"A": [0, 1, 2, 3, 4, 5, 6, 7]}) as path:
            self.assertEqual(
                parquet.read_pydict(path, ["A"], range(2, 5)), {"A": [2, 3, 4]}
            )

    def test_pydict_ignore_missing_rows(self):
        with parquet_file({"A": [0, 1, 2, 3]}) as path:
            self.assertEqual(
                parquet.read_pydict(path, ["A"], range(2, 5)), {"A": [2, 3]}
            )
