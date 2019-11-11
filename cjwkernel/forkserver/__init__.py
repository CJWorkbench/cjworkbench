from dataclasses import dataclass
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from typing import Any, BinaryIO, FrozenSet, List, Optional, Tuple
from . import protocol


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModuleProcess:
    process_name: str
    pid: int
    stdout: BinaryIO  # auto-closes in __del__
    stderr: BinaryIO  # auto-closes in __del__

    def kill(self) -> None:
        return os.kill(self.pid, 9)

    def wait(self, options: int) -> Tuple[int, int]:
        return os.waitpid(self.pid, options)


class Forkserver:
    """
    Launch Python quickly, sharing most memory pages.

    The problem this solves: we want to spin up many modules quickly; but as
    soon as a module starts running we can't trust it. Pyarrow+Pandas takes ~1s
    to import and costs ~100MB RAM.

    The solution: start up a mini-server, the "forkserver", which preloads
    pyarrow+pandas. fork() each time we need a subprocess. fork() is
    near-instantaneous. Beware: since fork() copies all memory, we must ensure
    the "forkserver" doesn't load anything sensitive before fork() (no Django:
    it reads secrets!); and we must ensure the "forkserver"'s child closes
    everything children shouldn't access (no control socket back to our web
    server!).

    Similar to Python's multiprocessing.forkserver, except...:

    * Children are not managed. It's up to the caller to kill and wait for the
      process. Modules are direct children of the _caller_, not of the
      forkserver.
    * asyncio-safe: we don't listen for SIGCHLD, because asyncio's
      subprocess-management routines override the signal handler.
    * Thread-safe: multiple threads may spawn multiple children, and they may
      all run concurrently.
    * No `multiprocessing.context`. This forkserver is the context.
    * No `Connection` (or other high-level constructs). Pass fds while forking.
    * The caller interacts with the forkserver process via _unnamed_ AF_UNIX
      socket, rather than a named socket. (`multiprocessing` writes a pipe
      to /tmp.) No messing with hmac. Instead, we mess with locks. ("Aren't
      locks worse?" -- [2019-09-30, adamhooper] probably not, because os.fork()
      is fast; and multiprocessing and asyncio have a race in Python 3.7.4 that
      causes forkserver children to exit with status code 255, so their
      named-pipe+hmac approach does not inspire confidence.)
    """

    def __init__(
        self,
        *,
        module_main: str = "cjwkernel.pandas.main.main",
        forkserver_preload: List[str] = [],
    ):
        # We rely on Python's os.fork() internals to close FDs and run a child
        # process.
        self._pid = os.getpid()
        self._socket, child_socket = socket.socketpair(socket.AF_UNIX)
        self._process = subprocess.Popen(
            [
                sys.executable,
                # PYTHONUNBUFFERED: parents read children's data sooner
                "-u",
                # Force UTF8 mode. We already set UTF8 at the OS level; but
                # let's be redundant because module authors would really
                # dislike it if our encoding changed.
                "-X",
                "utf8",
                "-c",
                'import cjwkernel.forkserver.main; cjwkernel.forkserver.main.forkserver_main("%s", %d)'
                % (module_main, child_socket.fileno()),
            ],
            env={
                # SECURITY: children inherit these values
                "LANG": "C.UTF-8",
                "HOME": "/",
                # [adamhooper, 2019-10-19] rrrgh, OpenBLAS....
                #
                # If we preload numpy, we're in trouble. Numpy loads OpenBLAS,
                # and OpenBLAS starts a whole threading subsystem ... which
                # breaks fork() in our modules. (We use fork() to open Parquet
                # files....) OPENBLAS_NUM_THREADS=1 disables the thread pool.
                #
                # I'm frustrated.
                "OPENBLAS_NUM_THREADS": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout.fileno(),
            stderr=sys.stderr.fileno(),
            close_fds=True,
            pass_fds=[child_socket.fileno()],
        )
        child_socket.close()
        self._lock = threading.Lock()

        with self._lock:
            message = protocol.ImportModules(forkserver_preload)
            message.send_on_socket(self._socket)

    def spawn_module(
        self,
        process_name: str,
        args: List[Any],
        *,
        chroot_dir: Optional[Path] = None,
        skip_sandbox_except: FrozenSet[str] = frozenset(),
    ) -> ModuleProcess:
        """
        Make our server spawn a process, and return it.

        `process_name` is the name to display in `ps` output and server logs.

        `args` are the arguments to pass to `cjwkernel.pandas.module.main()`.

        If `chroot_dir` is set, it must point to a directory on the filesystem.
        Remember that we call setuid() to an extreme UID (>65535) by default:
        that means the module will only be able to read files that are
        world-readable (i.e., "chmod o+r").

        (TODO `chroot_dir` should use pivot_root, for security. When Kubernetes
        lets us modify our mount namespace in an unprivileged container, switch
        to pivot_root.)

        `skip_sandbox_except` MUST BE EXACTLY `frozenset()`. Other values are
        only for unit tests. See `protocol.SpawnPandasModule` for details.
        """
        message = protocol.SpawnPandasModule(
            process_name=process_name,
            args=args,
            chroot_dir=chroot_dir,
            skip_sandbox_except=skip_sandbox_except,
        )
        with self._lock:
            message.send_on_socket(self._socket)
            response = protocol.SpawnedPandasModule.recv_on_socket(self._socket)
        return ModuleProcess(
            process_name=process_name,
            pid=response.pid,
            stdout=os.fdopen(response.stdout_fd, mode="rb"),
            stderr=os.fdopen(response.stderr_fd, mode="rb"),
        )

    def close(self) -> None:
        """
        Kill the forkserver.

        Spawned processes continue to run -- they are entirely disconnected
        from their forkserver.
        """
        self._socket.close()  # inspire self._process to exit of its own accord
        self._process.wait()
