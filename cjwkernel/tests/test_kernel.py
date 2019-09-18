from pathlib import Path
import shutil
import tempfile
import textwrap
import unittest
import pyarrow
from cjwkernel.errors import ModuleCompileError, ModuleExitedError
from cjwkernel.kernel import Kernel
from cjwkernel.tests.util import arrow_table_context, MockPath
from cjwkernel import types


class KernelTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.basedir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.basedir)
        super().tearDown()

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

    def test_compile_validate_bad_fetch_signature(self):
        kernel = Kernel()
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            kernel.compile(
                MockPath(["foo.py"], b"def fetch(table, params): return table"), "foo"
            )
        self.assertRegex(cm.exception.log, r"AssertionError")
        self.assertRegex(cm.exception.log, r"fetch must take one positional argument")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_render_arrow_instead_of_render(self):
        kernel = Kernel()
        result = kernel.compile(
            MockPath(
                ["foo.py"],
                b"from cjwkernel.types import RenderResult\ndef render_arrow(table, params, _1, _2, _3, output_path): return RenderResult()",
            ),
            "foo",
        )
        self.assertEquals(result.module_slug, "foo")
        self.assertIsInstance(result.marshalled_code_object, bytes)

    def test_compile_validate_happy_path(self):
        kernel = Kernel()
        result = kernel.compile(
            MockPath(["foo.py"], b"def render(table, params): return table"), "foo"
        )
        self.assertEquals(result.module_slug, "foo")
        self.assertIsInstance(result.marshalled_code_object, bytes)

    def test_compile_validate_works_with_dataclasses(self):
        """
        Test we can compile @dataclass

        @dataclass inspects `sys.modules`, so the module needs to be in
        `sys.modules` when @dataclass is run.
        """
        kernel = Kernel()
        result = kernel.compile(
            MockPath(
                ["foo.py"],
                textwrap.dedent(
                    """
                    from __future__ import annotations
                    from dataclasses import dataclass

                    def render(table, params):
                        return table

                    @dataclass
                    class A:
                        y: int
                    """
                ).encode("utf-8"),
            ),
            "foo",
        )
        self.assertEquals(result.module_slug, "foo")

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
        with arrow_table_context(
            {"A": [1, 2, 3], "B": ["a", "b", "c"]},
            columns=[
                types.Column("A", types.ColumnType.Number("{:,d}")),
                types.Column("B", types.ColumnType.Text()),
            ],
            dir=self.basedir,
        ) as input_table:
            with tempfile.NamedTemporaryFile(dir=self.basedir) as output_file:
                result = kernel.render(
                    module,
                    self.basedir,
                    input_table,
                    types.Params({"m": 2.5, "s": "XX"}),
                    types.Tab("tab-1", "Tab 1"),
                    None,
                    Path(output_file.name).name,
                )

                self.assertEquals(
                    result.table.table.to_pydict(),
                    {"A": [2.5, 5.0, 7.5], "B": ["aXX", "bXX", "cXX"]},
                )

    def test_fetch_happy_path(self):
        kernel = Kernel()
        module = kernel.compile(
            MockPath(
                ["foo.py"],
                b"import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [params['a']]})",
            ),
            "foo",
        )

        with tempfile.NamedTemporaryFile(dir=self.basedir) as output_file:
            result = kernel.fetch(
                module,
                self.basedir,
                types.Params({"a": 1}),
                {},
                None,
                None,
                Path(output_file.name).name,
            )

            self.assertEquals(result.errors, [])
            table = pyarrow.parquet.read_pandas(str(result.path))
            self.assertEquals(table.to_pydict(), {"A": [1]})
