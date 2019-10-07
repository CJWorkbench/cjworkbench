import array
import ctypes
import importlib
import os
import signal
import sys
import socket
import traceback
from typing import Callable
import cjwkernel.pandas.main
from . import protocol


libc = ctypes.CDLL("libc.so.6", use_errno=True)
PR_SET_NAME = 15
NR_clone = 56
NR_getpid = 39
# BEWARE: Docker, by default, disallows user-namespace cloning. We use Docker
# in development. Therefore we override Docker's seccomp profile to allow our
# clone() syscall to succeed. If you're adding to this list, also modify the
# seccomp profile we use in dev, unittest and integrationtest.
CLONE_PARENT = 0x00008000
CLONE_NEWUSER = 0x10000000
CLONE_NEWCGROUP = 0x02000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNS = 0x00020000  # new mount namespace


def _call_libc(fn, *args):
    """
    Call a libc function; raise OSError if it returns a negative number.

    Raise AttributeError if libc does not have an `fn` function.
    """
    func = getattr(libc, fn)  # raise AttributeError

    retval = func(*args)
    if retval < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "error calling %s(): %s" % (fn, os.strerror(errno)))
    return retval


_MODULE_STACK = ctypes.create_string_buffer(2 * 1024 * 1024)
"""
The memory area our child-module process will use for its stack.

Yup, this is low-level.
"""
_MODULE_STACK_POINTER = ctypes.c_void_p(
    ctypes.cast(_MODULE_STACK, ctypes.c_void_p).value + len(_MODULE_STACK)
)


# GLOBAL VARIABLES
#
# SECURITY: _any_ variable in "forkserver" is accessible to a "module" that it
# spawns. `del` will not delete the data.
#
# Our calling convention is: "forkserver uses global variables; module can see
# them." Rationale: to a malicious module, all variables are global anyway.
# "forkserver" should use very few variables, and they are all listed here.
module_main: Callable[..., None] = None
"""Function to call after sandboxing, with *message.args."""
sock: socket.socket = None
"""Socket "forkserver" uses to communicate with its parent."""
message: protocol.SpawnPandasModule = None
"""Arguments passed to the spawned module."""
stdout_read_fd: int = None
stdout_write_fd: int = None
stderr_read_fd: int = None
stderr_write_fd: int = None


def _sandbox_module():
    """
    Prevent module code from interacting with the rest of our system.

    Tasks with rationale ('[x]' means, "unit-tested"):

    [ ] Close `sock` (so "forkserver" does not misbehave)
    [ ] Close stdout/stderr (so modules do not flood logs; point
        stdout/stderr to `message.log_fd` instead)
    [ ] Remount /proc (so modules can't see other processes)
    """
    os.close(sock.fileno())  # Close `sock`
    global stdout_read_fd, stderr_read_fd
    os.close(stdout_read_fd)
    os.close(stderr_read_fd)
    stdout_read_fd = None
    stderr_read_fd = None
    _sandbox_stdout_stderr()  # Close stdout/stderr
    # _sandbox_remount_proc()  # Remount /proc


def _sandbox_stdout_stderr():
    global stdout_write_fd, stderr_write_fd
    os.dup2(stdout_write_fd, 1)
    os.dup2(stderr_write_fd, 2)
    os.close(stdout_write_fd)
    os.close(stderr_write_fd)
    stdout_write_fd = None
    stderr_write_fd = None


def _sandbox_remount_proc():
    _call_libc(
        "mount",
        ctypes.c_char_p(b"proc"),
        ctypes.c_char_p(b"/proc"),
        ctypes.c_char_p(b"proc"),
        0,
        0,
    )


def cloned_module_main() -> int:
    # Aid in debugging a bit
    name = "cjwkernel-module:%s" % message.process_name
    libc.prctl(PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)

    _sandbox_module()

    # Run the module code. This is what it's all about!
    #
    # It's normal for a module to raise an exception. That's probably a
    # developer error, and it's best to show the developer the problem --
    # exactly what `log_fd` is for. So we want to log exceptions to log_fd.
    #
    # SECURITY: it's possible for a module to try and fiddle with the stack or
    # heap to execute anything in memory. So this function might never return.
    # (Imagine `goto`.) That's okay -- we sandbox the module so it can't harm
    # us (aside from wasting CPU cycles), and we kill it after a timeout.
    try:
        module_main(*message.args)
    except:
        traceback.print_exc(sys.stderr.buffer.fileno())
        os._exit(1)

    # In the _common_ case ... exit here.
    os._exit(0)


_MODULE_MAIN_FUNC = ctypes.PYFUNCTYPE(ctypes.c_int)(cloned_module_main)


def spawn_module(sock: socket.socket, message: protocol.SpawnPandasModule) -> None:
    """
    Fork a child process; send its handle over `sock`; return.

    This closes all open file descriptors in the child: stdin, stdout, stderr,
    and `sock.fileno()`. The reason is SECURITY: the child will invoke
    user-provided code, so we bar everything it doesn't need. (Heck, it doesn't
    even get stdin+stdout+stderr!)

    There are three processes running concurrently here:

    * "parent": the Python process that holds a ForkServer handle. It sent
                `SpawnPandasModule` on `sock` and expects a response of
                `SpawnedPandasModule` (with "module_pid").
    * "forkserver": the forkserver_main() process. It called this function. It
                    has few file handles open -- by design. It spawns "module",
                    and sends "parent" the "module_pid" over `sock`.
    * "module": invokes `cjwkernel.pandas.main.main()`, using the file
                descriptors passed in `SpawnPandasModule`.
    """
    global stdout_read_fd, stdout_write_fd, stderr_read_fd, stderr_write_fd

    assert stdout_read_fd is None
    assert stdout_write_fd is None
    assert stderr_read_fd is None
    assert stderr_write_fd is None

    stdout_read_fd, stdout_write_fd = os.pipe()
    stderr_read_fd, stderr_write_fd = os.pipe()

    module_pid = _call_libc(
        "clone",
        _MODULE_MAIN_FUNC,
        _MODULE_STACK_POINTER,
        CLONE_PARENT | CLONE_NEWUSER | signal.SIGCHLD,
        0,
    )
    if module_pid < 0:
        raise OSError(ctypes.get_errno(), "clone() system call failed")
    assert module_pid != 0, "clone() should not return in the child process"

    os.close(stdout_write_fd)
    os.close(stderr_write_fd)
    stdout_write_fd = None
    stderr_write_fd = None

    spawned_module = protocol.SpawnedPandasModule(
        module_pid, stdout_read_fd, stderr_read_fd
    )
    spawned_module.send_on_socket(sock)

    os.close(stdout_read_fd)
    os.close(stderr_read_fd)
    stdout_read_fd = None
    stderr_read_fd = None


def forkserver_main(_module_main: str, socket_fd: int) -> None:
    """
    Start the forkserver.

    The init protocol ("a" means "parent" [class ForkServer], "b" means,
    "child" [forkserver_main()]):

    1a. Parent invokes forkserver_main(), passing AF_UNIX fd as argument.
    1b. Child calls socket.fromfd(), establishing a socket connection.
    2a. Parent sends ImportModules.
    2b. Child imports modules in its main (and only) thread.
    3a. Parent LOCKs
    4a. Parent creates fds and sends them through SpawnPandasModule().
    4b. Child forks and sends parent the PID. The returned PID is a *direct*
        child of parent (not of child) -- it got there via double-fork with
        "parent" having PR_SET_CHILD_SUBREAPER.
    5a. Parent receives PID from client.
    6a. Parent UNLOCKs
    7a. Parent reads from its fds and polls PID.

    For shutdown, the client simply closes its connection.

    The inevitable race: if "parent" doesn't read "module_pid" from the other
    end of "sock" and wait() for it, then nothing will wait() for the module
    process after it dies and it will become a zombie.
    """
    # Close fd=0 (stdin). No children should be able to read from stdin; and
    # forkserver_main has no reason to read from stdin, either.
    os.close(0)

    global module_main
    module_main_module_name, module_main_name = _module_main.rsplit(".", 1)
    module_main_module = importlib.import_module(module_main_module_name)
    module_main = module_main_module.__dict__[module_main_name]

    # 1b. Child establishes socket connection
    #
    # Note: we don't put this in a `with` block, because that would add a
    # finalizer. Finalizers will run in the "module_pid" process if
    # cjwkernel.pandas.main() raises an exception ... but the "module_pid"
    # process closes the socket before calling cjwkernel.pandas.main(), so the
    # finalizer would crash.
    global sock  # see GLOBAL VARIABLES comment
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=socket_fd)

    # 2b. Child imports modules in its main (and only) thread
    imports = protocol.ImportModules.recv_on_socket(sock)
    for im in imports.modules:
        __import__(im)

    while True:
        global message  # see GLOBAL VARIABLES comment
        try:
            # raise EOFError, RuntimeError
            message = protocol.SpawnPandasModule.recv_on_socket(sock)
        except EOFError:
            # shutdown: client closed its connection
            return

        # 4b. Child forks and sends parent the PID
        #
        # The _child_ sends `SpawnedPandasModule` over `sock`, because only
        # the child knows the sub-child's PID.
        spawn_module(sock, message)
