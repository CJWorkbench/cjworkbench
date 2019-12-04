import contextlib
from pathlib import Path
import unittest
from staticmodules import upload
from cjwkernel.tests.util import assert_arrow_table_equals
from cjwkernel.types import ArrowTable, I18nMessage, RenderError
from cjwkernel.util import tempfile_context


# See UploadFileViewTests for that
class UploadTest(unittest.TestCase):
    def setUp(self):
        self.ctx = contextlib.ExitStack()
        self.output_path = self.ctx.enter_context(tempfile_context(suffix=".arrow"))

    def tearDown(self):
        self.ctx.close()

    def _file(self, b: bytes, *, suffix) -> Path:
        path = self.ctx.enter_context(tempfile_context(suffix=suffix))
        path.write_bytes(b)
        return path

    def test_render_no_file(self):
        result = upload.render_arrow(
            ArrowTable(),
            {"file": None, "has_header": True},
            "tab-x",
            None,
            self.output_path,
        )
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(result.errors, [])

    def test_render_success(self):
        path = self._file(b"A,B\nx,y", suffix=".csv")
        result = upload.render_arrow(
            ArrowTable(),
            {"file": path, "has_header": True},
            "tab-x",
            None,
            self.output_path,
        )
        assert_arrow_table_equals(result.table, {"A": ["x"], "B": ["y"]})
        self.assertEqual(result.errors, [])

    def test_render_error(self):
        path = self._file(b"A,B\nx,y", suffix=".json")
        result = upload.render_arrow(
            ArrowTable(),
            {"file": path, "has_header": True},
            "tab-x",
            None,
            self.output_path,
        )
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    message=I18nMessage(
                        id="TODO_i18n",
                        args={"text": "JSON parse error at byte 0: Invalid value."},
                    ),
                    quick_fixes=[],
                )
            ],
        )
