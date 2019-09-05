from pathlib import Path
import unittest
import pyarrow
from cjwstate.tests.utils import MockPath
from cjwkernel.errors import ModuleCompileError, ModuleExitedError
from cjwkernel.kernel import Kernel
from cjwkernel.tests.util import arrow_file
from cjwkernel import types


class KernelTests(unittest.TestCase):
    def test_compile_syntax_error(self):
        kernel = Kernel()
        with self.assertRaises(ModuleCompileError):
            kernel.compile(
                MockPath(["foo.py"], b"de render(table, params): return table"), "foo"
            )

    def test_compile_validate_exited_error(self):
        kernel = Kernel()
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            kernel.compile(MockPath(["foo.py"], b"undefined()"), "foo")
        self.assertRegex(cm.exception.log, r"NameError")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_bad_render_signature(self):
        kernel = Kernel()
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            kernel.compile(
                MockPath(["foo.py"], b"def render(table, params, x): return table"),
                "foo",
            )
        self.assertRegex(cm.exception.log, r"AssertionError")
        self.assertRegex(cm.exception.log, r"render must take two positional arguments")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_happy_path(self):
        kernel = Kernel()
        result = kernel.compile(
            MockPath(["foo.py"], b"def render(table, params): return table"), "foo"
        )
        self.assertEquals(result.module_slug, "foo")
        self.assertIsInstance(result.marshalled_code_object, bytes)

    def test_migrate_params(self):
        kernel = Kernel()
        module = kernel.compile(
            MockPath(
                ["foo.py"], b"def migrate_params(params): return {'nested': params}"
            ),
            "foo",
        )
        result = kernel.migrate_params(module, {"foo": 123})
        self.assertEquals(result, {"nested": {"foo": 123}})

    def test_render_happy_path(self):
        kernel = Kernel()
        module = kernel.compile(
            MockPath(
                ["foo.py"],
                b"import pandas as pd\ndef render(table, params): return pd.DataFrame({'A': table['A'] * params['m'], 'B': table['B'] + params['s']})",
            ),
            "foo",
        )
        with arrow_file(
            pyarrow.Table.from_pydict({"A": [1, 2, 3], "B": ["a", "b", "c"]})
        ) as filename:
            result = kernel.render(
                module,
                types.ArrowTable(
                    Path(filename),
                    types.TableMetadata(
                        3,
                        [
                            types.Column("A", types.ColumnType.Number("{:,d}")),
                            types.Column("B", types.ColumnType.Text()),
                        ],
                    ),
                ),
                {"m": 2.5, "s": "XX"},
                types.Tab("tab-1", "Tab 1"),
                {},
                None,
            )
        try:
            self.assertEquals(
                result.table.table.to_pydict(),
                {"A": [2.5, 5.0, 7.5], "B": ["aXX", "bXX", "cXX"]},
            )
        finally:
            # TODO pass this path somewhere else ... perhaps in the `render()` signature?
            result.table.path.unlink()
