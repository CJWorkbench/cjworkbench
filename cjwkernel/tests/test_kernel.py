import unittest
from cjwstate.tests.utils import MockPath
from cjwkernel.errors import ModuleCompileError, ModuleExitedError
from cjwkernel.kernel import Kernel


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
