import contextlib
import os
from pathlib import Path
import shutil
import stat
from textwrap import dedent
from typing import Any, ContextManager, FrozenSet, List, Optional, Tuple
import unittest
from cjwkernel import forkserver
from cjwkernel.util import tempdir_context, tempfile_context


def module_main(indented_code: str) -> None:
    code = dedent(indented_code)
    code_obj = compile(code, "<module string>", "exec", dont_inherit=True, optimize=0)
    # Exec in global scope, so imports go to globals, not locals
    exec(code_obj, globals(), globals())


@contextlib.contextmanager
def _spawned_module_context(
    server: forkserver.Forkserver,
    args: List[Any] = [],
    chroot_dir: Optional[Path] = None,
    chroot_provide_paths: List[Tuple[Path, Path]] = [],
    skip_sandbox_except: FrozenSet[str] = frozenset(),
) -> ContextManager[forkserver.ModuleProcess]:
    subprocess = server.spawn_module(
        "forkserver-test",
        args,
        chroot_dir=chroot_dir,
        chroot_provide_paths=chroot_provide_paths,
        skip_sandbox_except=skip_sandbox_except,
    )
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

    def _spawn_and_communicate(
        self,
        indented_code: str,
        chroot_dir: Optional[Path] = None,
        chroot_provide_paths: List[Tuple[Path, Path]] = [],
        skip_sandbox_except: FrozenSet[str] = frozenset(),
    ) -> Tuple[int, bytes, bytes]:
        """
        Spawn, execute `indented_code`, and return (exitcode, stdout, stderr).

        This will never error.
        """
        with _spawned_module_context(
            self._forkserver,
            args=[indented_code],
            chroot_dir=chroot_dir,
            chroot_provide_paths=chroot_provide_paths,
            skip_sandbox_except=skip_sandbox_except,
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

    def _spawn_and_communicate_or_raise(
        self,
        indented_code: str,
        chroot_dir: Optional[Path] = None,
        chroot_provide_paths: List[Tuple[Path, Path]] = [],
        skip_sandbox_except: FrozenSet[str] = frozenset(),
    ) -> None:
        """
        Like _spawn_and_communicate(), but raise if exit code is not 0.
        """
        exitcode, stdout, stderr = self._spawn_and_communicate(
            indented_code,
            chroot_dir=chroot_dir,
            chroot_provide_paths=chroot_provide_paths,
            skip_sandbox_except=skip_sandbox_except,
        )
        self.assertEqual(exitcode, 0, "Exit code %d: %s" % (exitcode, stderr))
        self.assertEqual(stderr, b"", "Unexpected stderr: %r" % stderr)
        self.assertEqual(stdout, b"", "Unexpected stdout: %r" % stdout)

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

    def test_exception_goes_to_stderr(self):
        exitcode, stdout, stderr = self._spawn_and_communicate("import abaskjdgh")
        self.assertEqual(exitcode, 1)
        self.assertEqual(stdout, b"")
        self.assertRegex(stderr, b"ModuleNotFoundError")

    def test_SECURITY_wipe_env(self):
        self._spawn_and_communicate_or_raise(
            r"""
            import os
            env = dict(os.environ)
            assert env == {
                "LANG": "C.UTF-8",
                "HOME": "/",
            }, "Got wrong os.environ: %r" % env
            """
        )

    def test_SECURITY_sock_and_stdin_and_other_fds_are_closed(self):
        # The user cannot access pipes or files outside its sandbox (aside from
        # stdout+stderr, which the parent process knows are untrusted).
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

    def test_SECURITY_no_capabilities(self):
        # Even if the user becomes root, the Linux "capabilities" system
        # restricts syscalls that might leak outside the container.
        self._spawn_and_communicate_or_raise(
            r"""
            import ctypes
            import os
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            PR_CAP_AMBIENT = 47
            PR_CAP_AMBIENT_IS_SET = 1
            CAP_SYS_CHROOT = 18  # just one example
            EPERM = 1

            # Test a capability isn't set
            assert (
                libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_IS_SET, CAP_SYS_CHROOT, 0, 0)
            ) == 0
            # Test we can't actually *use* a capability -- chroot, for example

            try:
                os.chroot("/sys")  # raise on error
                assert False, "chroot worked after dropping capabilities?"
            except PermissionError:
                pass
            """,
            skip_sandbox_except=frozenset(["drop_capabilities"]),
        )

    def test_SECURITY_prevent_writing_uid_map(self):
        self._spawn_and_communicate_or_raise(
            r"""
            from pathlib import Path

            def assert_write_fails(path: str, text: str):
                try:
                    Path(path).write_text(text)
                except PermissionError:
                    pass
                else:
                    assert False, "Write to %s should have failed" % path

            assert_write_fails("/proc/self/uid_map", "0 0 65536")
            assert_write_fails("/proc/self/setgroups", "allow")
            assert_write_fails("/proc/self/gid_map", "0 0 65536")
            """,
            # There's no way to disable this security feature. But for testing
            # we must _disable_ setuid, drop_capabilities and chroot; so write
            # a dummy skip_sandbox_except to accomplish that.
            skip_sandbox_except=frozenset(["skip_all_optional_sandboxing"]),
        )

    def test_SECURITY_chroot_has_no_proc_dir(self):
        with tempdir_context() as root:
            self._spawn_and_communicate_or_raise(
                r"""
                import os

                assert not os.path.exists("/proc"), "/proc should not be accessible"
                assert not os.path.exists("/sys"), "/sys should not be accessible"
                """,
                chroot_dir=root,
                skip_sandbox_except=frozenset(["chroot"]),
            )

    def test_SECURITY_chroot_ensures_cwd_is_under_root(self):
        with tempdir_context() as root:
            self._spawn_and_communicate_or_raise(
                r"""
                import os

                assert os.getcwd() == "/"
                """,
                chroot_dir=root,
                skip_sandbox_except=frozenset(["chroot"]),
            )

    def test_SECURITY_provide_dir_readable(self):
        with tempdir_context() as root:
            with tempdir_context() as files:
                (files / "foo.txt").write_text("foo")
                (files / "subdir").mkdir(0o755)
                (files / "subdir" / "bar.bin").write_bytes(b"subbar")

                self._spawn_and_communicate_or_raise(
                    r"""
                    from pathlib import Path

                    assert Path("/data/foo.txt").read_text() == "foo"
                    assert Path("/data/subdir/bar.bin").read_text() == "subbar"
                    """,
                    chroot_dir=root,
                    chroot_provide_paths=[(Path("/data"), files)],
                    skip_sandbox_except=frozenset(["chroot"]),
                )

    def test_SECURITY_can_exec_statically_linked_program(self):
        with tempdir_context() as root:
            # Write /data.parquet within the subprocess itself. We can't use
            # `chroot_provide_paths` here because on dev machines, /app is a
            # volume mount while `root` is in the container image; os.link()
            # won't cross filesystems.
            parquet_bytes = (
                Path(__file__).parent.parent / "test_data" / "trivial.parquet"
            ).read_bytes()

            self._spawn_and_communicate_or_raise(
                r"""
                from pathlib import Path
                import subprocess
                Path("/data.parquet").write_bytes(%r)
                result = subprocess.run(
                    ["/usr/bin/parquet-to-text-stream", "/data.parquet", "csv"],
                    capture_output=True,
                )
                assert result.stderr == b"", "program errored %%r" %% result.stderr
                assert result.stdout == b"A\n1\n2", "program output %%r" %% result.stdout
                assert result.returncode == 0, "program exited with status code %%d" %% result.returncode
                """
                % parquet_bytes,
                chroot_dir=root,
                chroot_provide_paths=[
                    (
                        Path("/usr/bin/parquet-to-text-stream"),
                        Path("/usr/bin/parquet-to-text-stream"),
                    )
                ],
                skip_sandbox_except=frozenset(["chroot"]),
            )

    def test_SECURITY_setuid(self):
        # The user is not root
        self._spawn_and_communicate_or_raise(
            r"""
            import os
            assert os.getuid() == 1000
            assert os.getgid() == 1000
            # Assert the script can't setuid() to anything else. In other
            # words: test we really used setresuid(), not setuid() -- because
            # setuid() lets you un-setuid() later.
            #
            # This relies on the "drop_capabilities" sandboxing feature.
            # (Otherwise, the caller would have CAP_SETUID.)
            try:
                os.setuid(0); assert False, "gah, how did we setuid to 0?"
            except PermissionError:
                pass  # good
            """,
            skip_sandbox_except=frozenset(["setuid", "drop_capabilities"]),
        )

    def test_SECURITY_no_new_privs(self):
        # The user cannot use a setuid program to become root
        assert os.getuid() == 0  # so our test suite can actually chmod
        # Build the tempfile in the root filesystem, where there's no
        # "nosetuid" mount option
        with tempfile_context(prefix="print-id", suffix=".bin", dir="/") as prog:
            # We can't test with a _script_: we need to test with a _binary_.
            # (Scripts invoke the interpreter, which is not setuid.)
            #
            # The "id" binary is perfect: it prints all three uids and gids if
            # they differ from one another.
            shutil.copy("/usr/bin/id", prog)
            os.chown(str(prog), 0, 0)  # make doubly sure root owns it
            os.chmod(str(prog), 0o755 | stat.S_ISUID | stat.S_ISGID)
            exitcode, stdout, stderr = self._spawn_and_communicate(
                r"""
                import os
                os.execv("%s", ["%s"])
                """
                % (str(prog), str(prog)),
                # XXX SECURITY [2019-10-11] This test should fail if we comment
                # out "no_new_privs". Why doesn't it? (It looks like there's
                # some other security layer we don't know of....)
                skip_sandbox_except=frozenset(["setuid", "no_new_privs"]),
            )
            self.assertEqual(exitcode, 0)
            self.assertEqual(stdout, b"uid=1000 gid=1000 groups=1000\n")
            self.assertEqual(stderr, b"")
