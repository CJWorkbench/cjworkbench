import contextlib
import marshal
import os
from textwrap import dedent
from typing import Any, ContextManager, List, Tuple
import unittest
from cjwkernel import forkserver


def module_main(indented_code: str) -> None:
    code = dedent(indented_code)
    exec(code)


@contextlib.contextmanager
def _spawned_module_context(
    server: forkserver.Forkserver, args: List[Any] = []
) -> ContextManager[forkserver.ModuleProcess]:
    subprocess = server.spawn_module("forkserver-test", args)
    try:
        yield subprocess
    finally:
        try:
            subprocess.stdout.read()
        except ValueError:
            pass  # stdout already closed
        try:
            subprocess.stderr.read()
        except ValueError:
            pass  # stderr already closed
        try:
            subprocess.kill()
        except ProcessLookupError:
            pass
        try:
            subprocess.wait(0)
        except ChildProcessError:
            pass


class ForkserverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._forkserver = forkserver.Forkserver(
            module_main="cjwkernel.tests.forkserver.test_init.module_main"
        )

    @classmethod
    def tearDownClass(cls):
        cls._forkserver.close()
        del cls._forkserver

    def _spawn_and_communicate(self, indented_code: str) -> Tuple[int, bytes, bytes]:
        """
        Spawn, execute `indented_code`, and return (exitcode, stdout, stderr).

        This will never error.
        """
        with _spawned_module_context(
            self._forkserver, args=[indented_code]
        ) as subprocess:
            stdout = subprocess.stdout.read()
            stderr = subprocess.stderr.read()
            _, status = subprocess.wait(0)
            if os.WIFSIGNALED(status):
                exitcode = -os.WTERMSIG(status)
            elif os.WIFEXITED(status):
                exitcode = os.WEXITSTATUS(status)
            else:
                raise OSError("Unexpected status: %d" % status)
            return exitcode, stdout, stderr

    def _spawn_and_communicate_or_raise(self, indented_code: str) -> None:
        """
        Like _spawn_and_communicate(), but raise if exit code is not 0.
        """
        exitcode, stdout, stderr = self._spawn_and_communicate(indented_code)
        if exitcode != 0:
            raise AssertionError("Exit code %d: %s" % (exitcode, stderr))

    def test_stdout_stderr(self):
        exitcode, stdout, stderr = self._spawn_and_communicate(
            r"""
            import os
            import sys
            print("stdout")
            print("stderr", file=sys.stderr)
            sys.__stdout__.write("__stdout__\n")
            sys.__stderr__.write("__stderr__\n")
            os.write(1, b"fd1\n")
            os.write(2, b"fd2\n")
            """
        )
        self.assertEqual(exitcode, 0)
        self.assertEqual(stdout, b"stdout\n__stdout__\nfd1\n")
        self.assertEqual(stderr, b"stderr\n__stderr__\nfd2\n")

    def test_SECURITY_sock_and_stdin_and_other_fds_are_closed(self):
        self._spawn_and_communicate_or_raise(
            r"""
            import os
            for badfd in [0] + list(range(3, 20)):
                try:
                    os.write(badfd, b"x")
                    raise RuntimeError("fd %d is unexpectedly open" % badfd)
                except OSError as err:
                    assert err.args[0] == 9  # Bad file descriptor
            """
        )

    def test_exception_goes_to_stderr(self):
        exitcode, stdout, stderr = self._spawn_and_communicate("import abaskjdgh")
        self.assertEqual(exitcode, 1)
        self.assertEqual(stdout, b"")
        self.assertRegex(stderr, b"ModuleNotFoundError")
