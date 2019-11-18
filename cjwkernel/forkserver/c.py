import ctypes
import os
import signal
import struct
from typing import Callable


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


_CHILD_STACK = ctypes.create_string_buffer(2 * 1024 * 1024)
"""
The memory area our child process will use for its stack.

Yup, this is low-level.

It would be lovely if libc's clone() behaved like fork() instead of forcing
a stack and a function to jump to. (It looks like libc's clone() is great for
spawning threads and annoying for everything else.) It's tempting to use the
raw syscall instead ... but Linux's clone() syscall has a history of changing
signature ... so let's stick with libc.
"""
_RUN_CHILD_STACK_POINTER = ctypes.c_void_p(
    ctypes.cast(_CHILD_STACK, ctypes.c_void_p).value + len(_CHILD_STACK)
)

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


def _call_c_style(lib, fn, *args):
    """
    Call a libc-style function; raise OSError if it returns a negative number.

    Raise AttributeError if lib does not have an `fn` function.
    """
    func = getattr(lib, fn)  # raise AttributeError

    retval = func(*args)
    if retval < 0:
        errno = ctypes.get_errno()
        raise OSError(errno, "error calling %s(): %s" % (fn, os.strerror(errno)))
    return retval


def libc_prctl_pr_set_name(name: str) -> None:
    """
    Call prctl(PR_SET_NAME, ...).

    Raise OSError on error.
    """
    return _call_c_style(libc, "prctl", PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)


def libc_prctl_pr_set_no_new_privs(i: int) -> None:
    """
    Call prctl(PR_SET_NO_NEW_PRIVS, i, 0, 0, 0).
    """
    _call_c_style(libc, "prctl", PR_SET_NO_NEW_PRIVS, i, 0, 0, 0)


def libc_prctl_pr_set_seccomp_mode_filter(bpf_bytes: bytes) -> None:
    """
    Call prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, sock_fprog, 0, 0).

    This also _constructs_ the `sock_fprog` argument, because it's so
    low-level. The argument `bpf_bytes` must be a `bytes` object produced by
    `seccomp_export_bpf()`.
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

    _call_c_style(libc, "prctl", PR_SET_SECCOMP, SECCOMP_MODE_FILTER, sock_fprog, 0, 0)


def libc_clone(run_child: Callable[[], None]) -> int:
    """
    Spawn a subprocess that calls run_child().

    Raise OSError on error.

    The caller gets no control over the clone() flags. They are:

        * CLONE_PARENT -- parent, not forkserver, owns the subprocess.
        * CLONE_NEWNS -- new mount namespace
        * CLONE_NEWCGROUP -- new cgroup
        * CLONE_NEWUTS -- new UTS (hostname) namespace
        * CLONE_NEWIPC -- new IPC (shmem) namespace
        * CLONE_NEWUSER -- new user namespace
        * CLONE_NEWPID -- new PID namespace (children die when subprocess dies)
        * CLONE_NEWNET -- new network namespace (start with no Internet access)
        * signal.SIGCHLD -- send parent SIGCHLD on exit (the standard signal)
    """
    c_run_child = ctypes.PYFUNCTYPE(ctypes.c_int)(run_child)
    child_pid = _call_c_style(
        libc,
        "clone",
        c_run_child,
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
    assert child_pid != 0, "clone() should not return in the child process"
    return child_pid


def libc_prctl_set_securebits():
    """
    Prevent this process and its descendents from gaining capabilities.

    Capabilities will be dropped when switching to a non-root user. It's a
    one-way trip. Even executing a setuid-root program won't bring the
    capabilities back.
    """
    # straight from man capabilities(7):
    # "An  application  can  use  the following call to lock itself, and all of
    # its descendants, into an environment where the only way of gaining
    # capabilities is by executing a program with associated file capabilities"
    _call_c_style(
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


def libc_prctl_capbset_drop_all_capabilities():
    """
    Call prctl(PR_CAPBSET_DROP, cap, 0, 0, 0) for all capabilities.
    """
    for i in range(CAP_LAST_CAP + 1):
        _call_c_style(libc, "prctl", PR_CAPBSET_DROP, i, 0, 0, 0)


def libcap_cap_set_proc_empty_capabilities():
    """
    Call cap_set_proc(<empty>), dropping all capabilities.
    """
    empty_capabilities = libcap.cap_init()
    _call_c_style(libcap, "cap_set_proc", empty_capabilities)
    _call_c_style(libcap, "cap_free", empty_capabilities)
