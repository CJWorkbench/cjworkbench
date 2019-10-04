import shutil
import textwrap
import unittest
from unittest.mock import patch
import pyarrow
from cjwkernel.errors import ModuleCompileError, ModuleExitedError, ModuleTimeoutError
from cjwkernel.kernel import Kernel
from cjwkernel.tests.util import arrow_table_context, MockPath
from cjwkernel import forkserver, types
from cjwkernel.util import create_tempdir, tempfile_context


class KernelTests(unittest.TestCase):
    kernel = None

    @classmethod
    def setUpClass(cls):
        # Kernel takes a while to start up -- it's loading pyarrow+pandas in a
        # separate process. So we'll only load it once.
        cls.kernel = Kernel()

    @classmethod
    def tearDownClass(cls):
        del cls.kernel

    def setUp(self):
        super().setUp()
        self.basedir = create_tempdir()

    def tearDown(self):
        shutil.rmtree(self.basedir)
        super().tearDown()

    def test_compile_syntax_error(self):
        with self.assertRaises(ModuleCompileError):
            self.kernel.compile(
                MockPath(["foo.py"], b"de render(table, params): return table"), "foo"
            )

    def test_compile_validate_exited_error(self):
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            self.kernel.compile(MockPath(["foo.py"], b"undefined()"), "foo")
        self.assertRegex(cm.exception.log, r"NameError")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_bad_render_signature(self):
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            self.kernel.compile(
                MockPath(["foo.py"], b"def render(table, params, x): return table"),
                "foo",
            )
        self.assertRegex(cm.exception.log, r"AssertionError")
        self.assertRegex(cm.exception.log, r"render must take two positional arguments")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_bad_fetch_signature(self):
        with self.assertRaises(ModuleExitedError) as cm:
            # The child will print an assertion error to stderr.
            self.kernel.compile(
                MockPath(["foo.py"], b"def fetch(table, params): return table"), "foo"
            )
        self.assertRegex(cm.exception.log, r"AssertionError")
        self.assertRegex(cm.exception.log, r"fetch must take one positional argument")
        self.assertEqual(cm.exception.exit_code, 1)

    def test_compile_validate_render_arrow_instead_of_render(self):
        result = self.kernel.compile(
            MockPath(
                ["foo.py"],
                b"from cjwkernel.types import RenderResult\ndef render_arrow(table, params, _1, _2, _3, output_path): return RenderResult()",
            ),
            "foo",
        )
        self.assertEquals(result.module_slug, "foo")
        self.assertIsInstance(result.marshalled_code_object, bytes)

    def test_compile_validate_happy_path(self):
        result = self.kernel.compile(
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
        result = self.kernel.compile(
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
        module = self.kernel.compile(
            MockPath(
                ["foo.py"], b"def migrate_params(params): return {'nested': params}"
            ),
            "foo",
        )
        result = self.kernel.migrate_params(module, {"foo": 123})
        self.assertEquals(result, {"nested": {"foo": 123}})

    def test_migrate_params_retval_not_thrift_ready(self):
        module = self.kernel.compile(
            MockPath(["foo.py"], b"def migrate_params(params): return range(2)"), "foo"
        )
        with self.assertRaises(ModuleExitedError):
            self.kernel.migrate_params(module, {"foo": 123})

    def test_render_happy_path(self):
        module = self.kernel.compile(
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
            with tempfile_context(dir=self.basedir) as output_path:
                result = self.kernel.render(
                    module,
                    self.basedir,
                    input_table,
                    types.Params({"m": 2.5, "s": "XX"}),
                    types.Tab("tab-1", "Tab 1"),
                    None,
                    output_filename=output_path.name,
                )

                self.assertEquals(
                    result.table.table.to_pydict(),
                    {"A": [2.5, 5.0, 7.5], "B": ["aXX", "bXX", "cXX"]},
                )

    def test_render_exception(self):
        module = self.kernel.compile(
            MockPath(
                ["foo.py"],
                b"import os\ndef render(table, params): raise RuntimeError('fail')",
            ),
            "foo",
        )
        with self.assertRaises(ModuleExitedError) as cm:
            with arrow_table_context({"A": [1]}, dir=self.basedir) as input_table:
                with tempfile_context(dir=self.basedir) as output_path:
                    self.kernel.render(
                        module,
                        self.basedir,
                        input_table,
                        types.Params({"m": 2.5, "s": "XX"}),
                        types.Tab("tab-1", "Tab 1"),
                        None,
                        output_filename=output_path.name,
                    )

        self.assertEquals(cm.exception.exit_code, 1)  # Python exit code
        self.assertRegex(cm.exception.log, r"\bRuntimeError\b")
        self.assertRegex(cm.exception.log, r"\bfail\b")
        # Regression test: [2019-10-02], the "forkserver_main()->spawn_module()"
        # process would raise _another_ exception while exiting. It would try to
        # close an already-closed socket.
        self.assertNotRegex(cm.exception.log, r"Bad file descriptor")

    def test_render_killed_hard_out_of_memory(self):
        # This is similar to out-of-memory kill (but with different exit_code).
        # Testing out-of-memory is slow because we have to force the kernel to,
        # er, run out of memory. On a typical dev machine, that means filling
        # swap space -- gumming up the whole system. Not practical.
        #
        # In case of out-of-memory, the Linux out-of-memory killer will find
        # and kill a process using SIGKILL.
        #
        # So let's simulate that SIGKILL.
        module = self.kernel.compile(
            MockPath(
                ["foo.py"],
                b"import os\ndef render(table, params): os.kill(os.getpid(), 9)",
            ),
            "foo",
        )
        with self.assertRaises(ModuleExitedError) as cm:
            with arrow_table_context({"A": [1]}, dir=self.basedir) as input_table:
                with tempfile_context(dir=self.basedir) as output_path:
                    self.kernel.render(
                        module,
                        self.basedir,
                        input_table,
                        types.Params({"m": 2.5, "s": "XX"}),
                        types.Tab("tab-1", "Tab 1"),
                        None,
                        output_filename=output_path.name,
                    )

        self.assertEquals(cm.exception.exit_code, -9)  # SIGKILL
        self.assertEquals(cm.exception.log, "")

    def test_render_kill_timeout(self):
        module = self.kernel.compile(
            MockPath(
                ["foo.py"], b"import time\ndef render(table, params):\n  time.sleep(2)"
            ),
            "foo",
        )
        with patch.object(self.kernel, "render_timeout", 0.001):
            with self.assertRaises(ModuleTimeoutError):
                with arrow_table_context({"A": [1]}, dir=self.basedir) as input_table:
                    with tempfile_context(dir=self.basedir) as output_path:
                        self.kernel.render(
                            module,
                            self.basedir,
                            input_table,
                            types.Params({}),
                            types.Tab("tab-1", "Tab 1"),
                            None,
                            output_filename=output_path.name,
                        )

    def test_fetch_happy_path(self):
        module = self.kernel.compile(
            MockPath(
                ["foo.py"],
                b"import pandas as pd\ndef fetch(params): return pd.DataFrame({'A': [params['a']]})",
            ),
            "foo",
        )

        with tempfile_context(dir=self.basedir) as output_path:
            result = self.kernel.fetch(
                module,
                self.basedir,
                types.Params({"a": 1}),
                {},
                None,
                None,
                output_filename=output_path.name,
            )

            self.assertEquals(result.errors, [])
            table = pyarrow.parquet.read_pandas(str(result.path))
            self.assertEquals(table.to_pydict(), {"A": [1]})
