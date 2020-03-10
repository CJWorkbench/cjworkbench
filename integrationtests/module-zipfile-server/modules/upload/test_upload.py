import contextlib
import functools
import tempfile
import unittest
from pathlib import Path
from typing import ContextManager

import pyarrow
from cjwmodule.i18n import I18nMessage

import upload


def assert_arrow_table_equals(actual, expected):
    if actual is None or expected is None:
        assert (actual is None) == (expected is None)
    else:
        if isinstance(expected, dict):
            expected = pyarrow.table(expected)
        assert actual.column_names == expected.column_names
        assert actual.columns == expected.columns


def call_render(fn, params, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".arrow") as tf:
        output_path = Path(tf.name)
        errors = fn(None, params, output_path=output_path, **kwargs)
        if output_path.stat().st_size == 0:
            return None, errors
        else:
            with pyarrow.ipc.open_file(output_path) as reader:
                return reader.read_all(), errors


do_render = functools.partial(call_render, upload.render)


# See UploadFileViewTests for that
class UploadTest(unittest.TestCase):
    @contextlib.contextmanager
    def _file(self, b: bytes, *, suffix) -> ContextManager[Path]:
        with tempfile.NamedTemporaryFile(suffix=suffix) as tf:
            path = Path(tf.name)
            path.write_bytes(b)
            yield path

    def test_render_no_file(self):
        table, errors = do_render({"file": None, "has_header": True})
        assert_arrow_table_equals(table, None)
        self.assertEqual(errors, [])

    def test_render_success(self):
        with self._file(b"A,B\nx,y", suffix=".csv") as path:
            table, errors = do_render({"file": path, "has_header": True})
            assert_arrow_table_equals(table, {"A": ["x"], "B": ["y"]})
            self.assertEqual(errors, [])

    def test_render_error(self):
        with self._file(b"A,B\nx,y", suffix=".json") as path:
            table, errors = do_render({"file": path, "has_header": True})
            assert_arrow_table_equals(table, {})
            self.assertEqual(
                errors,
                [
                    I18nMessage(
                        "TODO_i18n",
                        {"text": "JSON parse error at byte 0: Invalid value."},
                        None,
                    )
                ],
            )
