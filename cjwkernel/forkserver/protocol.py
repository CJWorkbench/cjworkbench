from __future__ import annotations
import array
from dataclasses import dataclass, field, replace
from pathlib import Path
import pickle
from typing import Any, FrozenSet, List, Optional, Type, TypeVar
from multiprocessing.reduction import sendfds, recvfds
import shutil
import socket


_MessageType = TypeVar("T", bound="Message")


assert (
    shutil.rmtree.avoids_symlink_attacks
), "chroot is unusable: a child's symlinks can make a parent delete files"


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
class NetworkConfig:
    """
    Network configuration that lets children access the Internet.

    The kernel will create a veth interface and associated iptables rules to
    route traffic from the child to the Internet via network address
    translation (NAT). The iptables rules will prevent access to private IP
    addresses.

    We do not yet support IPv6, because Kubernetes support is shaky. Follow
    https://github.com/kubernetes/kubernetes/issues/62822.

    Here's how networking works. Each child process gets its own network
    namespace. The kernel creates a veth pair, and it passes the "child" veth
    interface to the child process. The kernel configures NAT from that device
    using iptables -- denying traffic to private network addresses (such as our
    Postgres database's address). The child process brings up its network
    interface and can only see the public Internet.

    After the child dies, the iptables rules are leaked. (This is fine, as of
    [2019-11-11], for the reason described in the next paragraph.)

    Beware if running multiple children at once that all access the Internet.
    Each must have a unique interface name and IP addresses. [2019-11-11] We
    only do networking with EDITABLE_CHROOT, which we use as a singleton.
    Therefore, we can use the same interface names and IP addresses with each
    invocation.

    The default values match those in `cjwkernel/setup-sandboxes.sh`. Don't
    edit one without editing the other.
    """

    kernel_veth_name: str = "cjw-veth-kernel"
    """
    Name of veth interface run by the kernel.

    Maximum length is 15 characters. Any longer gives NetlinkError 34.

    This name must not conflict with any other network device in the kernel's
    container.
    """

    child_veth_name: str = "cjw-veth-child"
    """
    Name of veth interface run by the child.

    Maximum length is 15 characters. Any longer gives NetlinkError 34.

    This name must not conflict with any other network device in the kernel's
    container. (The kernel creates this device before sending it into the
    child's network namespace.)
    """

    kernel_ipv4_address: str = "192.168.123.1"
    """
    IPv4 address of the kernel.

    This must not conflict with any other IP address in the kernel's container.

    This should be a private address. Be sure it doesn't conflict with your
    network's addresses. Kubernetes uses 10.0.0.0/8; Docker uses 172.16.0.0/12.
    The hard-coded "192.168.123/24" should be safe for Docker and Kubernetes.

    The child will use this address as its default gateway.
    """

    child_ipv4_address: str = "192.168.123.2"
    """
    IPv4 address of the child.

    The kernel will maintain iptables rules to route from this IP address to
    the public Internet.

    This must be in the same `/24` network block as `kernel_ipv4_address`.
    """


@dataclass(frozen=True)
class SpawnChild(MessageToChild):
    """
    Tell child to fork(), close this socket, and run child code.
    """

    process_name: str
    """Process name to display in 'ps' and server logs."""

    args: List[Any]
    """Arguments to pass to `child_main(*args)`."""

    chroot_dir: Optional[Path]
    """
    Setting for "chroot" security layer.

    If `chroot_dir` is set, it must point to a directory on the filesystem.
    """

    network_config: Optional[NetworkConfig]
    """
    If set, network configuration so child processes can access the Internet.

    If None, child processes have no network interfaces.
    """

    skip_sandbox_except: FrozenSet[str] = field(default_factory=frozenset)
    """
    Security layers to enable in child processes. (DO NOT USE IN PRODUCTION.)

    By default, child processes are sandboxed: user code should not be able to
    access the rest of the system. (In particular, it should not be able to
    access parent-process state; influence parent-process behavior in any way
    but its stdout, stderr and exit code; or communicate with any internal
    services.)
    
    Our layers of sandbox security overlap: for instance: we (a) restrict the
    user code to run as non-root _and_ (b) disallow root from escaping its
    chroot. We can't test layer (b) unless we disable layer (a); and that's
    what this feature is for.

    By default, all sandbox features are enabled. To enable only a subset, set
    `skip_sandbox_except` to a `frozenset()` with one or more of the following
    strings:

    * "drop_capabilities": limit root's capabilities
    """


@dataclass(frozen=True)
class SpawnedChild(MessageToParent):
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
        sendfds(sock, [self.stdin_fd, self.stdout_fd, self.stderr_fd])

    # override
    @classmethod
    def recv_on_socket(cls, sock: socket.socket) -> SpawnedChild:
        raw_message = super().recv_on_socket(sock)
        stdin_fd, stdout_fd, stderr_fd = recvfds(sock, 3)
        return replace(
            raw_message, stdin_fd=stdin_fd, stdout_fd=stdout_fd, stderr_fd=stderr_fd
        )
