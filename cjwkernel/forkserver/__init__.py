import ctypes
from dataclasses import dataclass
import logging
import os
import socket
import subprocess
import sys
import threading
from typing import Any, List, Tuple
from . import protocol
from cjwkernel.types import CompiledModule
from cjwkernel.pandas import main as module_main

libc = ctypes.CDLL("libc.so.6")
PR_SET_NAME = 15
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModuleProcess:
    module_slug: str
    pid: int

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

    def __init__(self, *, forkserver_preload: List[str] = []):
        # We rely on Python's os.fork() internals to close FDs and run a child
        # process.
        self._pid = os.getpid()
        self._socket, child_socket = socket.socketpair(socket.AF_UNIX)
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import cjwkernel.forkserver.main; cjwkernel.forkserver.main.forkserver_main(%d, %d)"
                % (self._pid, child_socket.fileno()),
            ],
            # env={},  # FIXME SECURITY set env so modules don't get secrets
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
        compiled_module: CompiledModule,
        output_fd: int,
        log_fd: int,
        function: str,
        args: List[Any],
    ) -> ModuleProcess:
        """
        Make our server spawn a process, and return it.

        `args` are the arguments to pass to `cjwkernel.pandas.module.main()`.
        """
        message = protocol.SpawnPandasModule(
            compiled_module=compiled_module,
            output_fd=output_fd,
            log_fd=log_fd,
            function=function,
            args=args,
        )
        with self._lock:
            message.send_on_socket(self._socket)
            response = protocol.SpawnedPandasModule.recv_on_socket(self._socket)
        return ModuleProcess(module_slug=compiled_module.module_slug, pid=response.pid)

    def close(self) -> None:
        """
        Kill the forkserver.

        Spawned processes continue to run -- they are entirely disconnected
        from their forkserver.
        """
        self._socket.close()  # inspire self._process to exit of its own accord
        self._process.wait()
