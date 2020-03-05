import contextlib
from pathlib import Path
from typing import ContextManager
import unittest
from staticmodules.upload import render
from cjwkernel.tests.util import assert_arrow_table_equals
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context


# See UploadFileViewTests for that
class UploadTest(unittest.TestCase):
    @contextlib.contextmanager
    def render(self, params):
        with tempfile_context(prefix="output-", suffix=".arrow") as output_path:
            errors = render(ArrowTable(), params, output_path)
            table = ArrowTable.from_arrow_file_with_inferred_metadata(output_path)
            yield RenderResult(table, [RenderError(I18nMessage(*e)) for e in errors])


    @contextlib.contextmanager
    def _file(self, b: bytes, *, suffix) -> ContextManager[Path]:
        with tempfile_context(suffix=suffix) as path:
            path.write_bytes(b)
            yield path

    def test_render_no_file(self):
        with self.render({"file": None, "has_header": True}) as result:
            assert_arrow_table_equals(result.table, {})
            self.assertEqual(result.errors, [])

    def test_render_success(self):
        with self._file(b"A,B\nx,y", suffix=".csv") as path:
            with self.render({"file": path, "has_header": True}) as result:
                assert_arrow_table_equals(result.table, {"A": ["x"], "B": ["y"]})
                self.assertEqual(result.errors, [])

    def test_render_error(self):
        with self._file(b"A,B\nx,y", suffix=".json") as path:
            with self.render({"file": path, "has_header": True}) as result:
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
