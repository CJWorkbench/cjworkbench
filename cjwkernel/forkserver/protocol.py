from __future__ import annotations
import array
from dataclasses import dataclass, replace
import pickle
from typing import Any, List, Type, TypeVar
from cjwkernel.types import CompiledModule
from multiprocessing.reduction import sendfds, recvfds
import socket


_MessageType = TypeVar("T", bound="Message")


class Message:
    def send_on_socket(self, sock: socket.socket) -> None:
        """
        Write this message to a UNIX socket.
        """
        blob = pickle.dumps(self)
        # Send length and then bytes
        sock.sendall(array.array("i", [len(blob)]).tobytes())
        sock.sendall(blob)

    @classmethod
    def recv_on_socket(cls: Type[_MessageType], sock: socket.socket) -> _MessageType:
        """
        Read a message of this type from a UNIX socket.

        The message must have been sent with `send_on_socket()`.

        Raise EOFError if the socket is closed mid-read.
        """
        len_array = array.array("i")
        len_blob = sock.recv(len_array.itemsize)
        if len_blob == b"":
            raise EOFError
        if len(len_blob) != len_array.itemsize:
            raise RuntimeError(
                "recv() returned partial length integer. We do not handle this."
            )
        len_array.frombytes(len_blob)
        n_bytes_to_read = len_array[0]

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


class MessageToChild(Message):
    pass


class MessageToParent(Message):
    pass


@dataclass(frozen=True)
class ImportModules(MessageToChild):
    """
    Tell child to import modules (in its own process).

    Whatever is imported here will be available to all spawned children.
    Don't import any module that might hold a reference to a secret!
    """

    modules: List[str]


@dataclass(frozen=True)
class SpawnPandasModule(MessageToChild):
    """
    Tell child to fork(), close this socket, and run child code.
    """

    process_name: str
    args: List[Any]


@dataclass(frozen=True)
class SpawnedPandasModule(MessageToParent):
    """
    Respond to SpawnPandasModule with a child process's information.
    """

    pid: int
    stdout_fd: int
    stderr_fd: int

    # override
    def send_on_socket(self, sock: socket.socket) -> None:
        """
        Write this message to a UNIX socket.

        As this message includes file descriptors, the recipient will need to
        receive different integers than the sender sends. First we send the
        sender's view of `self` using `pickle`; then we send the file
        descriptors using `sock.sendmsg()`.
        """

        super().send_on_socket(sock)
        # Now send the file descriptors.
        # https://docs.python.org/3/library/socket.html#socket.socket.sendmsg
        #
        # It turns out the multiprocessing.reduction module does exactly what
        # we want.
        sendfds(sock, [self.stdout_fd, self.stderr_fd])

    # override
    @classmethod
    def recv_on_socket(cls, sock: socket.socket) -> SpawnPandasModule:
        raw_message = super().recv_on_socket(sock)
        stdout_fd, stderr_fd = recvfds(sock, 2)
        return replace(raw_message, stdout_fd=stdout_fd, stderr_fd=stderr_fd)
