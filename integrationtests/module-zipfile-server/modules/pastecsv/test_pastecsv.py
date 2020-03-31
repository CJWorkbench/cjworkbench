import tempfile
import unittest
from pathlib import Path
from typing import List, NamedTuple

import pyarrow
from cjwmodule.i18n import I18nMessage

import pastecsv


class RenderResult(NamedTuple):
    table: pyarrow.Table
    errors: List[I18nMessage]


class Settings(NamedTuple):
    MAX_ROWS_PER_TABLE: int = 100
    MAX_COLUMNS_PER_TABLE: int = 100
    MAX_BYTES_PER_VALUE: int = 100
    MAX_CSV_BYTES: int = 100
    MAX_BYTES_TEXT_DATA: int = 100
    MAX_BYTES_PER_COLUMN_NAME: int = 100
    MAX_DICTIONARY_PYLIST_N_BYTES: int = 100
    MIN_DICTIONARY_COMPRESSION_RATIO_PYLIST_N_BYTES: float = 2.0
    SEP_DETECT_CHUNK_SIZE: int = 100


def assert_arrow_table_equals(actual, expected):
    if isinstance(expected, dict):
        expected = pyarrow.table(expected)
    assert actual.column_names == expected.column_names
    assert [c.type for c in actual.columns] == [c.type for c in expected.columns]
    assert actual.to_pydict() == expected.to_pydict()


def render_arrow(csv="", has_header_row=True, settings=Settings()):
    with tempfile.NamedTemporaryFile(suffix=".arrow") as tf:
        output_path = Path(tf.name)
        errors = pastecsv.render(
            None,
            dict(csv=csv, has_header_row=has_header_row),
            output_path,
            settings=settings,
        )
        with pyarrow.ipc.open_file(output_path) as reader:
            table = reader.read_all()
        return RenderResult(table, errors)


class PasteCSVTests(unittest.TestCase):
    def test_empty(self):
        result = render_arrow(csv="", has_header_row=True)
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(result.errors, [])

    def test_csv(self):
        result = render_arrow(csv="A,B\na,b\nc,d")
        assert_arrow_table_equals(result.table, {"A": ["a", "c"], "B": ["b", "d"]})
        self.assertEqual(result.errors, [])

    def test_tsv(self):
        result = render_arrow(csv="A\tB\na\tb\nc\td")
        assert_arrow_table_equals(result.table, {"A": ["a", "c"], "B": ["b", "d"]})
        self.assertEqual(result.errors, [])

    def test_extra_data_should_not_mangle_index(self):
        # Pandas' default behavior is _really_ weird when the number of values
        # in a row exceeds the number of headers. It tries building a
        # MultiIndex out of the first ones. This is probably so it can read its
        # own string representations? ... but it's terrible for our users.
        result = render_arrow(csv="A,B\na,b,c")
        assert_arrow_table_equals(
            result.table, {"A": ["a"], "B": ["b"], "Column 3": ["c"]}
        )
        self.assertEqual(
            result.errors,
            [
                I18nMessage(
                    "util.colnames.warnings.default",
                    {"n_columns": 1, "first_colname": "Column 3"},
                    "cjwmodule",
                )
            ],
        )

    def test_list_index_out_of_range(self):
        # Pandas' read_csv() freaks out on even the simplest examples....
        #
        # Today's exhibit:
        # pd.read_csv(io.StringIO('A\n,,'), index_col=False)
        # raises IndexError: list index out of range
        result = render_arrow(csv="A\n,,", has_header_row=True)
        assert_arrow_table_equals(
            result.table, {"A": [""], "Column 2": [""], "Column 3": [""]}
        )
        self.assertEqual(
            result.errors,
            [
                I18nMessage(
                    "util.colnames.warnings.default",
                    {"n_columns": 2, "first_colname": "Column 2"},
                    "cjwmodule",
                )
            ],
        )

    def test_no_header(self):
        result = render_arrow(csv="A,B", has_header_row=False)
        assert_arrow_table_equals(result.table, {"Column 1": ["A"], "Column 2": ["B"]})
        self.assertEqual(result.errors, [])

    def test_duplicate_column_names_renamed(self):
        result = render_arrow(csv="A,A\na,b", has_header_row=True)
        assert_arrow_table_equals(result.table, {"A": ["a"], "A 2": ["b"]})
        self.assertEqual(
            result.errors,
            [
                I18nMessage(
                    "util.colnames.warnings.numbered",
                    {"n_columns": 1, "first_colname": "A 2"},
                    "cjwmodule",
                )
            ],
        )

    def test_empty_column_name_gets_automatic_name(self):
        result = render_arrow(csv="A,,B\na,b,c", has_header_row=True)
        assert_arrow_table_equals(
            result.table, {"A": ["a"], "Column 2": ["b"], "B": ["c"]}
        )
        self.assertEqual(
            result.errors,
            [
                I18nMessage(
                    "util.colnames.warnings.default",
                    {"n_columns": 1, "first_colname": "Column 2"},
                    "cjwmodule",
                )
            ],
        )

    def test_no_nan(self):
        # https://www.pivotaltracker.com/story/show/163106728
        result = render_arrow(csv="A,B\nx,y\nz,NA")
        assert_arrow_table_equals(result.table, {"A": ["x", "z"], "B": ["y", "NA"]})
        self.assertEqual(result.errors, [])
