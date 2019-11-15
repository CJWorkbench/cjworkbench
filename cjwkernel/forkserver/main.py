import ctypes
import errno
import importlib
import os
from pathlib import Path
import pyroute2
import shutil
import signal
import socket
import struct
import traceback
from typing import Callable
from . import protocol


libc = ctypes.CDLL("libc.so.6", use_errno=True)
libcap = ctypes.CDLL("libcap.so.2", use_errno=True)
libcap.cap_init.restype = ctypes.c_void_p
libcap.cap_set_proc.argtypes = [ctypes.c_void_p]
libcap.cap_free.argtypes = [ctypes.c_void_p]
# <linux/prctl.h>
PR_SET_NAME = 15
PR_SET_SECCOMP = 22
PR_CAPBSET_DROP = 24
PR_SET_SECUREBITS = 28
PR_SET_NO_NEW_PRIVS = 38
# <linux/capability.h>
CAP_SETPCAP = 8
CAP_LAST_CAP = 37
# <linux/seccomp.h>
SECCOMP_MODE_FILTER = 2
# <linux/securebits.h>
SECBIT_KEEP_CAPS_LOCKED = 1 << 5
SECBIT_NO_SETUID_FIXUP = 1 << 2
SECBIT_NO_SETUID_FIXUP_LOCKED = 1 << 3
SECBIT_NOROOT = 1 << 0
SECBIT_NOROOT_LOCKED = 1 << 1

# BEWARE: Docker, by default, disallows user-namespace cloning. We use Docker
# in development. Therefore we override Docker's seccomp profile to allow our
# clone() syscall to succeed. If you're adding to this list, also modify the
# seccomp profile we use in dev, unittest and integrationtest.
# <linux/sched.h>
CLONE_PARENT = 0x00008000
CLONE_NEWNS = 0x00020000
CLONE_NEWCGROUP = 0x02000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000


def _call_c(lib, fn, *args):
    """
    Call a libc function; raise OSError if it returns a negative number.

    Raise AttributeError if libc does not have an `fn` function.
    """
    func = getattr(lib, fn)  # raise AttributeError

    retval = func(*args)
    if retval < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "error calling %s(): %s" % (fn, os.strerror(errno)))
    return retval


_CHILD_STACK = ctypes.create_string_buffer(2 * 1024 * 1024)
"""
The memory area our child process will use for its stack.

Yup, this is low-level.
"""
_RUN_CHILD_STACK_POINTER = ctypes.c_void_p(
    ctypes.cast(_CHILD_STACK, ctypes.c_void_p).value + len(_CHILD_STACK)
)


# GLOBAL VARIABLES
#
# SECURITY: _any_ variable in "forkserver" is accessible to a child it spawns.
# `del` will not delete the data.
#
# Our calling convention is: "forkserver uses global variables; child can see
# them." Rationale: to a malicious child, all variables are global anyway.
# "forkserver" should use very few variables, and they are all listed here.
child_main: Callable[..., None] = None
"""Function to call after sandboxing, with *message.args."""
sock: socket.socket = None
"""Socket "forkserver" uses to communicate with its parent."""
message: protocol.SpawnChild = None
"""Arguments passed to the spawned child."""
stdin_read_fd: int = None
stdin_write_fd: int = None
stdout_read_fd: int = None
stdout_write_fd: int = None
stderr_read_fd: int = None
stderr_write_fd: int = None
is_namespace_ready_read_fd: int = None
is_namespace_ready_write_fd: int = None


def _should_sandbox(feature: str) -> bool:
    """
    Return `True` if we should call a particular sandbox function.

    This should _always_ return `True` on production code. The function only
    exists to help with unit testing.
    """
    if message.skip_sandbox_except:
        # test code only
        return feature in message.skip_sandbox_except
    else:
        # production code
        return True


def _sandbox_child():
    """
    Prevent child code from interacting with the rest of our system.

    Tasks with rationale ('[x]' means, "unit-tested"):

    [x] Wait for forkserver to write uid_map
    [x] Close `sock` (so "forkserver" does not misbehave)
    [x] Drop capabilities (like CAP_SYS_ADMIN)
    [x] Set seccomp filter
    [x] Setuid to 1000
    [x] Use chroot (so children can't see other files)
    """
    # Wait for parent to close the is_namespace_ready pipe
    os.read(is_namespace_ready_read_fd, 1)
    os.close(is_namespace_ready_read_fd)

    # Read seccomp data before we chroot().
    seccomp_bpf_bytes = Path(__file__).with_name("sandbox-seccomp.bpf").read_bytes()

    if message.network_config is not None:
        _sandbox_network(message.network_config)
    if _should_sandbox("no_new_privs"):
        _sandbox_no_new_privs()
    if message.chroot_dir is not None:
        _sandbox_chroot(message.chroot_dir)
    if _should_sandbox("setuid"):
        _sandbox_setuid()
    if _should_sandbox("drop_capabilities"):
        _sandbox_drop_capabilities()
    if _should_sandbox("seccomp"):
        _sandbox_seccomp(seccomp_bpf_bytes)


def _rewrite_stdin_stdout_stderr():
    """
    Rewrite fds 0, 1, 2 to stdin_read_fd, stdout_write_fd, stderr_write_fd.

    Close the original stdin_read_fd, stdout_write_fd and stderr_write_fd.

    After this, `sys.stdin`, `sys.stdout` and `sys.stderr` will point to our
    new file descriptors. There will be no way to access the _parent_'s
    file descriptors (the original fds 0, 1 and 2) -- those will be closed.

    Why call this? Well, first of all, these are our communication channels
    with the parent process. But there's also a security reason: the parent's
    stdout and stderr are used for logging. User code must not be allowed to
    flood our server logs; therefore, user code must not access the parent's
    stdout and stderr.
    """
    global stdin_read_fd, stdout_write_fd, stderr_write_fd
    for passed_fd, want_fd in [
        (stdin_read_fd, 0),
        (stdout_write_fd, 1),
        (stderr_write_fd, 2),
    ]:
        # Handle an edge case: passed_fd may coincidentally be want_fd, if
        # forkserver closes file descriptors on init and they get reused.
        if passed_fd != want_fd:
            os.dup2(passed_fd, want_fd)
            os.close(passed_fd)
    stdin_read_fd = None
    stdout_write_fd = None
    stderr_write_fd = None


def _sandbox_network(config: protocol.NetworkConfig) -> None:
    """
    Set up networking, assuming forkserver passed us a network interface.

    Set ip address of veth interface, then bring it up.

    Also bring up the "lo" interface.

    This requires CAP_NET_ADMIN. Use the "drop_capabilities" sandboxing step
    afterwards to prevent further fiddling.
    """
    with pyroute2.IPRoute() as ipr:
        lo_index = ipr.link_lookup(ifname="lo")[0]
        ipr.link("set", index=lo_index, state="up")

        veth_index = ipr.link_lookup(ifname=config.child_veth_name)[0]
        ipr.addr(
            "add", index=veth_index, address=config.child_ipv4_address, prefixlen=24
        )
        ipr.link("set", index=veth_index, state="up")
        ipr.route("add", gateway=config.kernel_ipv4_address)


def _write_namespace_uidgid(child_pid: int) -> None:
    """
    Write /proc/child_pid/uid_map and /proc/child_pid/gid_map.

    Why call this? Because otherwise, the called code can do it for us. That
    would mean root in the child would be equal to root in the parent -- so the
    child could, for instance, modify files owned outside of it.

    ref: man user_namespaces(7).
    """
    Path(f"/proc/{child_pid}/uid_map").write_text("0 100000 65536")
    Path(f"/proc/{child_pid}/setgroups").write_text("deny")
    Path(f"/proc/{child_pid}/gid_map").write_text("0 100000 65536")


def _copy_chroot_file(src: str, dst: str) -> None:
    """
    Try os.link(); if it's a cross-device link, use shutil.copy2().

    This is designed to be used by shutil.copytree().
    """
    # try os.link() and return if it works
    try:
        return os.link(src, dst)
        # ... _return_. This is the end of it.
    except OSError as err:
        if err.errno == errno.EXDEV:
            # cross-device link: fall through.
            # (Let's not pollute the stack trace by calling shutil.copy2()
            # within the exception handler.)
            pass
        else:
            raise

    # fallback: shutil.copy2()
    return shutil.copy2(src, dst)


def _sandbox_chroot(root: Path) -> None:
    """
    Enter a restricted filesystem, so absolute paths are relative to `root`.

    Why call this? So the user can't read files from our filesystem (which
    include our secrets and our users' secrets); and the user can't *write*
    files to our filesystem (which might inject code into a parent process).

    SECURITY: entering a chroot is not enough. To prevent this process from
    accessing files outside the chroot, this process must drop its ability to
    chroot back _out_ of the chroot. Use _sandbox_drop_capabilities().

    SECURITY: TODO: switch from chroot to pivot_root. pivot_root makes it far
    harder for root to break out of the jail. It needs a process-specific mount
    namespace. But on Kubernetes (and Docker), we'd need so many privileges to
    pivot_root that we'd be _decreasing_ security. Find out how to do it with
    fewer privileges.

    For now, since we don't use a separate mount namespace, chroot doesn't
    add much "security" in the case of privilege escalation: root will be able
    to escape the chroot. (Even root doesn't have permission to read our
    secrets, though.) Chroot isn't to allay evildoers: it's so child-code
    developers see the filesystem tree we want them to see.
    """
    os.chroot(str(root))
    os.chdir("/")


def _sandbox_drop_capabilities():
    """
    Drop all capabilities in the caller.

    Also, set the process "securebits" to prevent regaining capabilities.

    Why call this? So if user code manages to setuid to root (which should be
    impossible), it still won't have permission to call dangerous kernel code.
    (For example: after dropping privileges, "pivot_root" will fail with
    EPERM, even for root.)

    ref: http://people.redhat.com/sgrubb/libcap-ng/
    ref: man capabilities(7)
    """
    # straight from man capabilities(7):
    # "An  application  can  use  the following call to lock itself, and all of
    # its descendants, into an environment where the only way of gaining
    # capabilities is by executing a program with associated file capabilities"
    _call_c(
        libc,
        "prctl",
        PR_SET_SECUREBITS,
        (
            SECBIT_KEEP_CAPS_LOCKED
            | SECBIT_NO_SETUID_FIXUP
            | SECBIT_NO_SETUID_FIXUP_LOCKED
            | SECBIT_NOROOT
            | SECBIT_NOROOT_LOCKED
        ),
        0,
        0,
        0,
    )

    # And now, _drop_ the capabilities (and we can never gain them again)
    # Drop the Bounding set...
    for i in range(CAP_LAST_CAP + 1):
        _call_c(libc, "prctl", PR_CAPBSET_DROP, i, 0, 0, 0)
    # ... and drop permitted/effective/inheritable capabilities
    empty_capabilities = libcap.cap_init()
    _call_c(libcap, "cap_set_proc", empty_capabilities)
    _call_c(libcap, "cap_free", empty_capabilities)


def _sandbox_no_new_privs():
    """
    Prevent a setuid bit on a file from restoring capabilities.
    """
    _call_c(libc, "prctl", PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)


def _sandbox_seccomp(bpf_bytes):
    """
    Install a whitelist filter to prevent unwanted syscalls.

    Why call this? Two reasons:

    1. Redundancy: if there's a Linux bug, there's a good chance our seccomp
       filter may prevent an attacker from exploiting it.
    2. Speculative execution: seccomp implicitly prevents _all_ syscalls from
       exploiting Spectre-type CPU security bypasses.

    Docker comes with seccomp by default, making seccomp mostly redundant. But
    Kubernetes 1.14 still doesn't use seccomp, and [2019-11-07] that's what we
    use on prod.

    To maintain our whitelist, read `docker/seccomp/README.md`. The compiled
    file, for x86-64, belongs in `cjwkernel/forkserver/sandbox-seccomp.bpf`.

    Requires `no_new_privs` sandbox (or CAP_SYS_ADMIN).
    """
    # seccomp arg must be a pointer to:
    #
    # struct sock_fprog {
    #     unsigned short len; /* Number of filter blocks */
    #     struct sock_filter* filter;
    # }
    #
    # ... and we'll emulate that with raw bytes.
    #
    # Our seccomp.bpf file contains the bytes for `filter`. Calculate `len`.
    # (We call it `n_blocks` because `len` is taken in Python.)
    #
    # Each filter is:
    #
    # struct sock_filter {	/* Filter block */
    # 	__u16	code;   /* Actual filter code */
    # 	__u8	jt;	/* Jump true */
    # 	__u8	jf;	/* Jump false */
    # 	__u32	k;      /* Generic multiuse field */
    # };
    #
    # ... for a total of 8 bytes (64 bits) per filter.

    n_blocks = len(bpf_bytes) // 8

    # Pack a sock_fprog struct. With a pointer in it.
    bpf_buf = ctypes.create_string_buffer(bpf_bytes)
    sock_fprog = struct.pack("HL", n_blocks, ctypes.addressof(bpf_buf))

    _call_c(libc, "prctl", PR_SET_SECCOMP, SECCOMP_MODE_FILTER, sock_fprog, 0, 0)


def _sandbox_setuid():
    """
    Drop root: switch to UID 1000.

    Why call this? Because Linux gives special capabilities to root (even after
    we drop privileges).

    ref: man setresuid(2)
    """
    os.setresuid(1000, 1000, 1000)
    os.setresgid(1000, 1000, 1000)


def _close_parent_fds() -> None:
    """
    Close file descriptors "owned" by forkserver.

    This is called by both the parent and the child.

    When the parent calls clone(), it has open file descriptors for _its_ end
    of UNIX pipes.

    The child must close these pipes which were duplicated by clone().
    Otherwise, then pipes will never close, so the child will never be able to
    read() until the pipe closes. (read() will deadlock.)

    As for the parent: it sends stdin+stdout+stderr file descriptors to _its_
    parent, duplicating them. After that, it should close them to prevent
    leaking or deadlocking.
    """
    global stdin_write_fd, stdout_read_fd, stderr_read_fd, is_namespace_ready_write_fd
    os.close(stdin_write_fd)
    os.close(stdout_read_fd)
    os.close(stderr_read_fd)
    os.close(is_namespace_ready_write_fd)
    stdin_write_fd = None
    stdout_read_fd = None
    stderr_read_fd = None
    is_namespace_ready_write_fd = None


def run_child() -> int:
    # Set process name seen in "ps". Helps find PID when debugging.
    name = "forked-child:%s" % message.process_name
    _call_c(libc, "prctl", PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)

    global sock
    os.close(sock.fileno())
    sock = None

    _close_parent_fds()
    _rewrite_stdin_stdout_stderr()

    _sandbox_child()

    # Run the child code. This is what it's all about!
    #
    # It's normal for child code to raise an exception. That's probably a
    # developer error, and it's best to show the developer the problem --
    # exactly what `stderr` is for. So we log exceptions to stderr.
    #
    # SECURITY: it's possible for a child to try and fiddle with the stack or
    # heap to execute anything in memory. So this function might never return.
    # (Imagine `goto`.) That's okay -- we sandbox the child so it can't harm
    # us (aside from wasting CPU cycles). The parent may choose to kill the
    # child after a timeout.
    try:
        child_main(*message.args)
    except:
        traceback.print_exc()
        os._exit(1)

    # In the _common_ case ... exit here.
    os._exit(0)


_RUN_CHILD_FUNC = ctypes.PYFUNCTYPE(ctypes.c_int)(run_child)


def _setup_network_namespace_from_forkserver(
    config: protocol.NetworkConfig, child_pid: int
) -> None:
    """
    Send new veth device to `child_pid`'s network namespace.

    See `_sandbox_network()` for the child's logic. Read the `NetworkConfig`
    docstring to understand how the network namespace works.
    """
    with pyroute2.IPRoute() as ipr:
        # Avoid a race: what if another forked process already created this
        # interface?
        #
        # If that's the case, assume the other process has already exited
        # (because [2019-11-11] we only run one networking-enabled child at a
        # time). So the veth device is about to be deleted anyway.
        try:
            ipr.link("del", ifname=config.kernel_veth_name)
        except pyroute2.NetlinkError as err:
            if err.code == errno.ENODEV:
                pass  # common case -- the device doesn't exist
            else:
                raise

        # Create kernel_veth + child_veth veth pair
        ipr.link(
            "add",
            ifname=config.kernel_veth_name,
            peer=config.child_veth_name,
            kind="veth",
        )

        # Bring up kernel_veth
        kernel_veth_index = ipr.link_lookup(ifname=config.kernel_veth_name)[0]
        ipr.addr(
            "add",
            index=kernel_veth_index,
            address=config.kernel_ipv4_address,
            prefixlen=24,
        )
        ipr.link("set", index=kernel_veth_index, state="up")

        # Send child_veth to child namespace
        child_veth_index = ipr.link_lookup(ifname=config.child_veth_name)[0]
        ipr.link("set", index=child_veth_index, net_ns_pid=child_pid)


def spawn_child(sock: socket.socket, message: protocol.SpawnChild) -> None:
    """
    Fork a child process; send its handle over `sock`; return.

    This closes all open file descriptors in the child: stdin, stdout, stderr,
    and `sock.fileno()`. The reason is SECURITY: the child will invoke
    user-provided code, so we bar everything it doesn't need. (Heck, it doesn't
    even get stdin+stdout+stderr!)

    There are three processes running concurrently here:

    * "parent": the Python process that holds a ForkServer handle. It sent
                `SpawnChild` on `sock` and expects a response of `SpawnedChild`
                (with "child_pid").
    * "forkserver": the forkserver_main() process. It called this function. It
                    has few file handles open -- by design. It spawns "child",
                    and sends "parent" the "child_pid" over `sock`.
    * "child": invokes `child_main()`.
    """
    global stdin_write_fd, stdin_read_fd, stdout_read_fd, stdout_write_fd, stderr_read_fd, stderr_write_fd, is_namespace_ready_read_fd, is_namespace_ready_write_fd

    assert stdin_write_fd is None
    assert stdin_read_fd is None
    assert stdout_read_fd is None
    assert stdout_write_fd is None
    assert stderr_read_fd is None
    assert stderr_write_fd is None
    assert is_namespace_ready_read_fd is None
    assert is_namespace_ready_write_fd is None

    stdin_read_fd, stdin_write_fd = os.pipe()
    stdout_read_fd, stdout_write_fd = os.pipe()
    stderr_read_fd, stderr_write_fd = os.pipe()
    is_namespace_ready_read_fd, is_namespace_ready_write_fd = os.pipe()

    child_pid = _call_c(
        libc,
        "clone",
        _RUN_CHILD_FUNC,
        _RUN_CHILD_STACK_POINTER,
        CLONE_PARENT
        | CLONE_NEWNS
        | CLONE_NEWCGROUP
        | CLONE_NEWUTS
        | CLONE_NEWIPC
        | CLONE_NEWUSER
        | CLONE_NEWPID
        | CLONE_NEWNET
        | signal.SIGCHLD,
        0,
    )
    if child_pid < 0:
        raise OSError(ctypes.get_errno(), "clone() system call failed")
    assert child_pid != 0, "clone() should not return in the child process"

    # close fds meant exclusively for the child
    os.close(stdin_read_fd)
    os.close(stdout_write_fd)
    os.close(stderr_write_fd)
    os.close(is_namespace_ready_read_fd)
    stdin_read_fd = None
    stdout_write_fd = None
    stderr_write_fd = None
    is_namespace_ready_read_fd = None

    # Sandbox the child from the forkserver side of things. (To avoid races,
    # the child waits for us to close is_namespace_ready_write_fd before
    # continuing with its own sandboxing.)
    #
    # Do this sandboxing before returning the PID to the parent process.
    # Otherwise, the parent could kill the process before we're done sandboxing
    # it (and we'd need to recover from that race).
    _write_namespace_uidgid(child_pid)
    if message.network_config is not None:
        _setup_network_namespace_from_forkserver(message.network_config, child_pid)

    # Send our lovely new process to the caller (parent process)
    spawned_child = protocol.SpawnedChild(
        child_pid, stdin_write_fd, stdout_read_fd, stderr_read_fd
    )
    spawned_child.send_on_socket(sock)

    _close_parent_fds()  # closes is_namespace_ready_write_fd


def forkserver_main(_child_main: str, socket_fd: int) -> None:
    """
    Start the forkserver.

    The init protocol ("a" means "parent" [class ForkServer], "b" means,
    "forkserver" [forkserver_main()]; "c" means, "child" [run_child()]):

    1a. Parent invokes forkserver_main(), passing AF_UNIX fd as argument.
    1b. Forkserver calls socket.fromfd(), establishing a socket connection.
    2a. Parent sends ImportModules.
    2b. Forkserver imports modules in its main (and only) thread.
    3b. Forkserver waits for a message from parent.
    4a. Parent sends a message with spawn parameters.
    4b. Forkserver opens pipes for file descriptors, calls clone(), and sends
        a response to Parent with pid and (stdin, stdout, stderr) descriptors.
    4c. Child waits for forkserver to close its file descriptors.
    5a. Parent receives PID and descriptors from Forkserver.
    5b. Forkserver closes its file descriptors and waits for parent again.
    5c. Child sandboxes itself and calls child code with stdin/stdout/stderr.
    6a. Parent writes to child's stdin, reads from its stdout, and waits for
        its PID.
    6c. Child reads from stdin, writes to stdout, and exits.

    For shutdown, the client simply closes its connection.

    The inevitable race: if "parent" doesn't read "child_pid" from the other
    end of "sock" and wait() for it, then nothing will wait() for the child
    process after it dies and it will become a zombie child of "parent".
    """
    # Load the function we'll call in clone() children
    global child_main
    child_main_module_name, child_main_name = _child_main.rsplit(".", 1)
    child_main_module = importlib.import_module(child_main_module_name)
    child_main = child_main_module.__dict__[child_main_name]

    # 1b. Forkserver establishes socket connection
    #
    # Note: we don't put this in a `with` block, because that would add a
    # finalizer. Finalizers would run in the "child" process; but our child
    # closes the socket as a security precaution, so the finalizer would
    # crash.
    #
    # (As a rule, forkserver shouldn't use try/finally or context managers.)
    global sock  # see GLOBAL VARIABLES comment
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=socket_fd)

    # 2b. Forkserver imports modules in its main (and only) thread
    imports = protocol.ImportModules.recv_on_socket(sock)
    for im in imports.modules:
        __import__(im)

    while True:
        # 4a. Parent sends a message with spawn parameters.
        global message  # see GLOBAL VARIABLES comment
        try:
            # raise EOFError, RuntimeError
            message = protocol.SpawnChild.recv_on_socket(sock)
        except EOFError:
            # shutdown: client closed its connection
            return

        # 4b. Forkserver calls clone() and sends a response to Parent.
        spawn_child(sock, message)
