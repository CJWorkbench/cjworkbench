import unittest
from cjwkernel.errors import (
    ModuleError,
    ModuleExitedError,
    ModuleTimeoutError,
    format_for_user_debugging,
)


class FormatForUserDebuggingTests(unittest.TestCase):
    def test_timeout_error(self):
        self.assertEqual(
            format_for_user_debugging(ModuleTimeoutError("x", 5.0)), "timed out"
        )

    def test_exited_sigkill(self):
        self.assertEqual(
            format_for_user_debugging(ModuleExitedError("x", -9, "")), "SIGKILL"
        )

    def test_exited_sigsys(self):
        self.assertEqual(
            # SIGSYS usually means "seccomp killed you"
            format_for_user_debugging(ModuleExitedError("x", -31, "")),
            "SIGSYS",
        )

    def test_exited_stack_trace(self):
        self.assertEqual(
            format_for_user_debugging(
                ModuleExitedError(
                    "x",
                    1,
                    """\n  File "/app/cjwkernel/errors.py", line 1, in <module>\n    import signals\nModuleNotFoundError: No module named 'signals'\n""",
                )
            ),
            "exit code 1: ModuleNotFoundError: No module named 'signals'",
        )

    def test_exited_unknown_with_message(self):
        self.assertEqual(
            format_for_user_debugging(ModuleError("unknown error")),
            "ModuleError: unknown error",
        )

    def test_exited_unknown_without_message(self):
        self.assertEqual(format_for_user_debugging(ModuleError()), "ModuleError")
