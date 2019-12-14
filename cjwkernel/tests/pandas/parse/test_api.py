import contextlib
from pathlib import Path
from typing import ContextManager
import unittest
from cjwkernel.pandas.parse.mime import MimeType
from cjwkernel.pandas.parse.api import parse_file
from cjwkernel.tests.util import assert_arrow_table_equals, tempfile_context
from cjwkernel.types import I18nMessage, RenderError


TestDataPath = Path(__file__).parent.parent.parent / "test_data"


@contextlib.contextmanager
def _data_file(b: bytes, *, suffix: str = "") -> ContextManager[Path]:
    with tempfile_context(".input", suffix=suffix) as data_path:
        data_path.write_bytes(b)
        yield data_path


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.ctx = contextlib.ExitStack()
        self.output_path = self.ctx.enter_context(tempfile_context(suffix=".arrow"))

    def tearDown(self):
        self.ctx.close()

    def test_detect_csv_by_suffix(self):
        with _data_file(b"A,B\nx,y\nz,a", suffix=".csv") as csv_path:
            result = parse_file(csv_path, output_path=self.output_path)
        assert_arrow_table_equals(result.table, {"A": ["x", "z"], "B": ["y", "a"]})

    def test_detect_tsv_by_suffix(self):
        with _data_file(b"A\tB\nx\ty\nz\ta", suffix=".tsv") as tsv_path:
            result = parse_file(tsv_path, output_path=self.output_path)
        assert_arrow_table_equals(result.table, {"A": ["x", "z"], "B": ["y", "a"]})

    def test_detect_semicolon_csv_by_suffix(self):
        with _data_file(b"A;B\nx;y\nz;a", suffix=".txt") as txt_path:
            result = parse_file(txt_path, output_path=self.output_path)
        assert_arrow_table_equals(result.table, {"A": ["x", "z"], "B": ["y", "a"]})

    def test_csv_has_header_false(self):
        with _data_file(b"A\n1.00\n2") as path:
            result = parse_file(
                path,
                output_path=self.output_path,
                mime_type=MimeType.CSV,
                has_header=False,
            )
        assert_arrow_table_equals(result.table, {"Column 1": ["A", "1.00", "2"]})

    def test_csv_detect_encoding_by_default(self):
        with _data_file("A\ncafé".encode("windows-1252")) as path:
            result = parse_file(
                path,
                output_path=self.output_path,
                mime_type=MimeType.CSV,
                encoding=None,
            )
        assert_arrow_table_equals(result.table, {"A": ["café"]})

    def test_csv_override_encoding_by_argument(self):
        # caller-selected encoding overrides autodetected encoding
        with _data_file("A\ncafé".encode("utf-8")) as path:
            result = parse_file(
                path,
                output_path=self.output_path,
                mime_type=MimeType.CSV,
                encoding="windows-1252",
            )
        assert_arrow_table_equals(result.table, {"A": ["cafÃ©"]})

    def test_detect_json_by_suffix(self):
        with _data_file(b'[{"X":"x"}]', suffix=".json") as json_path:
            result = parse_file(json_path, output_path=self.output_path)
        assert_arrow_table_equals(result.table, {"X": ["x"]})

    def test_json_detect_encoding_by_default(self):
        with _data_file('[{"A":"café"}]'.encode("windows-1252")) as path:
            result = parse_file(
                path,
                output_path=self.output_path,
                mime_type=MimeType.JSON,
                encoding=None,
            )
        assert_arrow_table_equals(result.table, {"A": ["café"]})

    def test_json_override_encoding_by_argument(self):
        # caller-selected encoding overrides autodetected encoding
        with _data_file('[{"A":"café"}]'.encode("utf-8")) as path:
            result = parse_file(
                path,
                output_path=self.output_path,
                mime_type=MimeType.JSON,
                encoding="windows-1252",
            )
        assert_arrow_table_equals(result.table, {"A": ["cafÃ©"]})

    def test_detect_xlsx_by_suffix(self):
        result = parse_file(TestDataPath / "test.xlsx", output_path=self.output_path)
        assert_arrow_table_equals(
            result.table, {"Month": ["Jan", "Feb"], "Amount": [10, 20]}
        )

    def test_xlsx_has_header_false(self):
        result = parse_file(
            TestDataPath / "test.xlsx", output_path=self.output_path, has_header=False
        )
        assert_arrow_table_equals(
            result.table,
            {"Column 1": ["Month", "Jan", "Feb"], "Column 2": ["Amount", "10", "20"]},
        )

    def test_detect_xls_by_suffix(self):
        result = parse_file(TestDataPath / "example.xls", output_path=self.output_path)
        assert_arrow_table_equals(result.table, {"foo": [1, 2], "bar": [2, 3]})

    def test_detect_unknown_file_extension(self):
        with _data_file(b"A,B\nx,y", suffix=".bin") as bin_path:
            result = parse_file(bin_path, output_path=self.output_path)
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage.TODO_i18n(
                        "Unknown file extension '.bin'. Please try a different file."
                    )
                )
            ],
        )

    def test_mime_type_overrides_suffix(self):
        # File is ".csv" but we parse as ".json" because mime_type=MimeType.JSON
        with _data_file(b'[{"X":"x"}]', suffix=".csv") as json_path:
            result = parse_file(
                json_path, output_path=self.output_path, mime_type=MimeType.JSON
            )
        assert_arrow_table_equals(result.table, {"X": ["x"]})
