"""
Communications between parent and pycloner.

We assume trust between these two processes. (The SpawnChild message is
transmitted in Python's pickle format.)
"""
from __future__ import annotations
import array
from dataclasses import dataclass
import pickle
from typing import Any, List
from multiprocessing.reduction import sendfds, recvfds
import socket
from .sandbox import NetworkConfig, SandboxConfig


__all__ = ["NetworkConfig", "SandboxConfig", "SpawnChild", "SpawnedChild"]


class Message:
    def send_on_socket(self, sock: socket.socket):
        raise NotImplementedError

    @classmethod
    def recv_on_socket(cls, sock: socket.socket):
        raise NotImplementedError


def _send_i(sock: socket.socket, i: int) -> None:
    sock.sendall(array.array("i", [i]).tobytes())


def _recv_i(sock: socket.socket) -> int:
    arr = array.array("i")
    blob = sock.recv(arr.itemsize)
    if blob == b"":
        raise EOFError
    if len(blob) != arr.itemsize:
        raise RuntimeError(
            "recv() returned partial length integer. We do not handle this."
        )
    arr.frombytes(blob)
    return arr[0]


@dataclass(frozen=True)
class SpawnChild:
    """
    Tell child to fork(), close this socket, and run child code.
    """

    process_name: str
    """Process name to display in 'ps' and server logs."""

    args: List[Any]
    """Arguments to pass to `child_main(*args)`."""

    sandbox_config: SandboxConfig
    """Restrictions to place on the child's abilities."""

    def send_on_socket(self, sock: socket.socket) -> None:
        """
        Write this message to a UNIX socket.
        """
        blob = pickle.dumps(self)
        # Send length and then bytes
        _send_i(sock, len(blob))
        sock.sendall(blob)

    @classmethod
    def recv_on_socket(cls, sock: socket.socket) -> SpawnChild:
        """
        Read a message of this type from a UNIX socket.

        The message must have been sent with `send_on_socket()`.

        Raise EOFError if the socket is closed mid-read.
        """
        n_bytes_to_read = _recv_i(sock)

        # there's no sock.recvall(). https://bugs.python.org/issue1103213
        blobs = []
        while n_bytes_to_read > 0:
            # Python docs suggest 4096 as max size:
            # https://docs.python.org/3/library/socket.html#socket.socket.recv
            blob = sock.recv(min(4096, n_bytes_to_read))
            if len(blob) == 0:
                raise RuntimeError(
                    "Missing %d bytes reading %r" % (n_bytes_to_read, cls)
                )
            blobs.append(blob)
            n_bytes_to_read -= len(blob)
        blob = b"".join(blobs)
        retval = pickle.loads(blob)
        if type(retval) != cls:
            raise ValueError("Received blob %r; expected type %r" % (retval, cls))
        return retval


@dataclass(frozen=True)
class SpawnedChild(Message):
    """
    Respond to SpawnChild with a child process's information.
    """

    pid: int
    stdin_fd: int
    stdout_fd: int
    stderr_fd: int

    # override
    def send_on_socket(self, sock: socket.socket) -> None:
        """
        Write this message to a UNIX socket.

        As this message includes file descriptors, the recipient will need to
        receive different integers than the sender sends. We send file
        descriptors using `sock.sendmsg()`.
        """

        # Send PID
        _send_i(sock, self.pid)
        # Now send the file descriptors.
        # https://docs.python.org/3/library/socket.html#socket.socket.sendmsg
        #
        # It turns out the multiprocessing.reduction module does exactly what
        # we want.
        sendfds(sock, [self.stdin_fd, self.stdout_fd, self.stderr_fd])

    # override
    @classmethod
    def recv_on_socket(cls, sock: socket.socket) -> SpawnedChild:
        pid = _recv_i(sock)
        stdin_fd, stdout_fd, stderr_fd = recvfds(sock, 3)
        return cls(pid, stdin_fd, stdout_fd, stderr_fd)
