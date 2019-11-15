from dataclasses import dataclass
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from typing import Any, BinaryIO, Dict, FrozenSet, List, Optional, Tuple
from . import protocol


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChildProcess:
    process_name: str
    pid: int
    stdin: BinaryIO  # auto-closes in __del__
    stdout: BinaryIO  # auto-closes in __del__
    stderr: BinaryIO  # auto-closes in __del__

    def kill(self) -> None:
        return os.kill(self.pid, 9)

    def wait(self, options: int) -> Tuple[int, int]:
        return os.waitpid(self.pid, options)


class Forkserver:
    """
    Launch Python quickly, sharing most memory pages.

    The problem this solves: we want to spin up many children quickly; but as
    soon as a child starts running we can't trust it. Starting Python with lots
    of imports like Pyarrow+Pandas can take ~2s and cost ~100MB RAM.

    The solution: start up a mini-server, the "forkserver", which preloads
    Python modules. clone() each time we need a subprocess. clone() is
    near-instantaneous. Beware: since clone() copies all memory, the
    "forkserver" shouldn't load anything sensitive before clone(). (No Django:
    it reads secrets!). Also, the "forkserver"'s child should close everything
    children before executing user code so it can't fiddle with the control
    socket.

    Similar to Python's multiprocessing.forkserver, except...:

    * Children are not managed. It's up to the caller to kill and wait for the
      process. Children are direct children of the _caller_, not of the
      forkserver. (We use CLONE_PARENT.)
    * asyncio-safe: we don't listen for SIGCHLD, because asyncio's
      subprocess-management routines override the signal handler.
    * Thread-safe: multiple threads may spawn multiple children, and they may
      all run concurrently (unless child code writes files or uses networking).
    * No `multiprocessing.context`. This forkserver is the context.
    * No `Connection` (or other high-level constructs).
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
        child_main: str = "cjwkernel.pandas.main.main",
        environment: Dict[str, Any] = {},
        preload_imports: List[str] = [],
    ):
        # We rely on Python's os.fork() internals to close FDs and run a child
        # process.
        self._pid = os.getpid()
        self._socket, child_socket = socket.socketpair(socket.AF_UNIX)
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-u",  # PYTHONUNBUFFERED: parents read children's data sooner
                "-c",
                'import cjwkernel.forkserver.main; cjwkernel.forkserver.main.forkserver_main("%s", %d)'
                % (child_main, child_socket.fileno()),
            ],
            # SECURITY: children inherit these values
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout.fileno(),
            stderr=sys.stderr.fileno(),
            close_fds=True,
            pass_fds=[child_socket.fileno()],
        )
        child_socket.close()
        self._lock = threading.Lock()

        with self._lock:
            message = protocol.ImportModules(preload_imports)
            message.send_on_socket(self._socket)

    def spawn_child(
        self,
        process_name: str,
        args: List[Any],
        *,
        chroot_dir: Optional[Path] = None,
        network_config: Optional[protocol.NetworkConfig] = None,
        skip_sandbox_except: FrozenSet[str] = frozenset(),
    ) -> ChildProcess:
        """
        Make our server spawn a process, and return it.

        `process_name` is the name to display in `ps` output and server logs.

        `args` are the arguments to pass to `child_main()`.

        If `chroot_dir` is set, it must point to a directory on the filesystem.
        Remember that we call setuid() to an extreme UID (>65535) by default:
        that means the child will only be able to read files that are
        world-readable (i.e., "chmod o+r").

        (TODO `chroot_dir` should use pivot_root, for security. When Kubernetes
        lets us modify our mount namespace in an unprivileged container, switch
        to pivot_root.)

        `skip_sandbox_except` MUST BE EXACTLY `frozenset()`. Other values are
        only for unit tests. See `protocol.SpawnChild` for details.
        """
        message = protocol.SpawnChild(
            process_name=process_name,
            args=args,
            chroot_dir=chroot_dir,
            network_config=network_config,
            skip_sandbox_except=skip_sandbox_except,
        )
        with self._lock:
            message.send_on_socket(self._socket)
            response = protocol.SpawnedChild.recv_on_socket(self._socket)
        return ChildProcess(
            process_name=process_name,
            pid=response.pid,
            stdin=os.fdopen(response.stdin_fd, mode="wb"),
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
