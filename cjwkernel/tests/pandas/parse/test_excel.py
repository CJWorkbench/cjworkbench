from pathlib import Path
import unittest
from cjwkernel.pandas.parse.excel import parse_xls_file, parse_xlsx_file
from cjwkernel.tests.util import assert_arrow_table_equals, tempfile_context
from cjwkernel.types import I18nMessage, RenderError


TestDataPath = Path(__file__).parent.parent.parent / "test_data"


class ParseOtherTests(unittest.TestCase):
    def test_xlsx(self):
        path = TestDataPath / "test.xlsx"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xlsx_file(
                path, output_path=output_path, has_header=True, autoconvert_types=True
            )
        assert_arrow_table_equals(
            result.table, {"Month": ["Jan", "Feb"], "Amount": [10, 20]}
        )
        self.assertEqual(result.errors, [])

    def test_xls(self):
        path = TestDataPath / "example.xls"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xls_file(
                path, output_path=output_path, has_header=True, autoconvert_types=True
            )
        assert_arrow_table_equals(result.table, {"foo": [1, 2], "bar": [2, 3]})
        self.assertEqual(result.errors, [])

    def test_xlsx_cast_colnames_to_str(self):
        path = TestDataPath / "all-numeric.xlsx"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xlsx_file(
                path, output_path=output_path, has_header=True, autoconvert_types=True
            )
        assert_arrow_table_equals(result.table, {"1": [2]})
        self.assertEqual(result.errors, [])

    def test_xlsx_invalid(self):
        with tempfile_context(prefix="invalid", suffix=".xlsx") as path:
            path.write_bytes(b"not an xlsx")
            with tempfile_context(suffix=".arrow") as output_path:
                result = parse_xlsx_file(
                    path,
                    output_path=output_path,
                    has_header=True,
                    autoconvert_types=True,
                )

        assert_arrow_table_equals(result.table, {})
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "py.cjwkernel.pandas.parse.excel.parse_xls_file.XLRDError",
                        {
                            "error": "Unsupported format, or corrupt file: Expected BOF record; found b'not an x'"
                        },
                    )
                )
            ],
        )

    def test_xlsx_nix_control_characters_from_colnames(self):
        path = TestDataPath / "headers-have-control-characters.xlsx"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xlsx_file(
                path, output_path=output_path, has_header=True, autoconvert_types=False
            )
        assert_arrow_table_equals(result.table, {"AB": ["a"], "C": ["b"]})
        self.assertEqual(result.errors, [])

    def test_xlsx_uniquify_colnames(self):
        path = TestDataPath / "headers-have-duplicate-colnames.xlsx"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xlsx_file(
                path, output_path=output_path, has_header=True, autoconvert_types=False
            )
        # Should be:
        # assert_arrow_table_equals(result.table, {"A": ["a"], "A 2": ["b"]})
        assert_arrow_table_equals(result.table, {"A": ["a"], "A.1": ["b"]})
        self.assertEqual(result.errors, [])

    def test_xlsx_replace_empty_colnames(self):
        path = TestDataPath / "headers-empty.xlsx"
        with tempfile_context(suffix=".arrow") as output_path:
            result = parse_xlsx_file(
                path, output_path=output_path, has_header=True, autoconvert_types=False
            )
        # Should be:
        # assert_arrow_table_equals(result.table, {"A": ["a"], "Column 2": ["b"]})
        assert_arrow_table_equals(result.table, {"A": ["a"], "Unnamed: 1": ["b"]})
        self.assertEqual(result.errors, [])
