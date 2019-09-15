from datetime import datetime
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pyarrow
from cjwkernel.tests.util import arrow_table, assert_arrow_table_equals
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

    def test_read_write_text(self):
        self._test_read_write_table({"A": ["x", None, "y"]})

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
