from __future__ import annotations
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class CloneFds:
    """
    File descriptors cloned by pycloner into child during spawn.

    These are a sequence of read/write pairs. Here's how they're all used.
    (Glossary: here, "parent" is pycloner's parent; "pycloner" is the main
    process; and "child" is a newly-spawned child. We only spawn once at a
    time.)

        * stdin: the child process's stdin. pycloner sends `stdin_w` to
                 parent. child moves `stdin_r` to become fd 0.
        * stdout: the child process's stdout. pycloner sends `stdout_r` to
                  parent. child moves `stdout_r` to become fd 1.
        * stderr: the child process's stderr. pycloner sends `stderr_r` to
                  parent. child moves `stderr_r` to become fd 1.
        * is_namespace_ready: a simple semaphore. pycloner closes
                              `is_namespace_ready_w` when it's finished with
                              bookkeeping. child waits for
                              `is_namespare_ready_r` to be closed before
                              delving into sandboxing.

    SANITY: all these file descriptors must be closed in the child: that's
    our contract with child code. (stdin_r, stdout_w and stderr_w should be
    dup2()d to fds 0, 1 and 2 first.)

    SANITY: all these file descriptors must be closed in pycloner: otherwise,
    they will leak to future children.

    To be abundantly clear: these file descriptors are all opened once. Then
    there's a clone() call. They must be closed *twice*: once by pycloner,
    once by the child.

    Here's an illustration:

        PYCLONER:
            clone_fds = CloneFds.create()
            child_pid = clone() [spawning CHILD _and_ continuing]
            pycloner_fds = clone_fds.become_pycloner()
            prepare_namespace_for_child(child_pid)
            parent_fds = pycloner_fds.signal_namespace_is_ready()
            send_fds_to_parent(parent_fds)
            parent_fds.close()
            # Now all the fds are closed
            clone_fds = None  # so we're back to a blank slate

        CHILD:
            child_fds = clone_fds.become_child()
            std_fds = child_fds.wait_for_namespace_ready()
            std_fds.replace_this_process_standard_fds()
            # Now all the fds are closed.
    """

    stdin_r: int
    stdin_w: int
    stdout_r: int
    stdout_w: int
    stderr_r: int
    stderr_w: int
    is_namespace_ready_r: int
    is_namespace_ready_w: int

    @classmethod
    def create(cls) -> CloneFds:
        stdin_r, stdin_w = os.pipe()
        stdout_r, stdout_w = os.pipe()
        stderr_r, stderr_w = os.pipe()
        is_namespace_ready_r, is_namespace_ready_w = os.pipe()
        return cls(
            stdin_r,
            stdin_w,
            stdout_r,
            stdout_w,
            stderr_r,
            stderr_w,
            is_namespace_ready_r,
            is_namespace_ready_w,
        )

    def become_child(self) -> ChildFds:
        """
        Close file descriptors owned by pycloner.

        (clone() copied all these file descriptors, but pycloner and child
        need to divvy them up and close the ones they don't own.
        """
        for fd in (
            self.stdin_w,
            self.stdout_r,
            self.stderr_r,
            self.is_namespace_ready_w,
        ):
            os.close(fd)
        return ChildFds(
            self.stdin_r, self.stdout_w, self.stderr_w, self.is_namespace_ready_r
        )

    def become_pycloner(self) -> PyclonerFds:
        """
        Close file descriptors owned by the child.

        (clone() copied all these file descriptors, but pycloner and child
        need to divvy them up and close the ones they don't own.
        """
        for fd in (
            self.stdin_r,
            self.stdout_w,
            self.stderr_w,
            self.is_namespace_ready_r,
        ):
            os.close(fd)
        return PyclonerFds(
            self.stdin_w, self.stdout_r, self.stderr_r, self.is_namespace_ready_w
        )


@dataclass(frozen=True)
class ChildFds:
    """
    File descriptors owned by the child process.

    The child must call fds.wait_for_namespace_ready() to progress.
    """

    stdin_r: int
    stdout_w: int
    stderr_w: int
    is_namespace_ready_r: int

    def wait_for_namespace_ready(self) -> ChildStdFds:
        # Wait for parent to close its is_namespace_ready_w
        os.read(self.is_namespace_ready_r, 1)
        os.close(self.is_namespace_ready_r)
        return ChildStdFds(self.stdin_r, self.stdout_w, self.stderr_w)


@dataclass(frozen=True)
class ChildStdFds:
    """
    File descriptors that must become input/output/error.

    The child must call fds.replace_this_process_standard_fds() to progress.
    """

    stdin_r: int
    stdout_w: int
    stderr_w: int

    def replace_this_process_standard_fds(self) -> None:
        """
        Overwrite this process's file descriptors 0, 1 and 2.

        Close the original FDs.

        After this, `sys.stdin`, `sys.stdout` and `sys.stderr` will use our
        new descriptors. there will be no way to access pycloner's file
        descriptors (the original fds 0, 1 and 2) -- those will be closed.
        """
        # Be careful: if we close stdin on pycloner, then os.pipe() may
        # reuse fd 0. Ditto stdout/stderr.
        #
        # This if-statement algorithm is compatible with any fd numbers (even
        # 0, 1 and 2) ... so long as stdin_r < stdout_w < stderr_w.
        assert self.stdin_r < self.stdout_w
        assert self.stdout_w < self.stderr_w
        if self.stdin_r != 0:
            os.dup2(self.stdin_r, 0)
            os.close(self.stdin_r)
        if self.stdout_w != 1:
            os.dup2(self.stdout_w, 1)
            os.close(self.stdout_w)
        if self.stderr_w != 2:
            os.dup2(self.stderr_w, 2)
            os.close(self.stderr_w)


@dataclass(frozen=True)
class PyclonerFds:
    """
    File descriptors owned by the pycloner process.

    The pycloner must call fds.signal_namespace_is_ready() to progress.
    """

    stdin_w: int
    stdout_r: int
    stderr_r: int
    is_namespace_ready_w: int

    def signal_namespace_is_ready(self) -> ParentFds:
        os.close(self.is_namespace_ready_w)
        return ParentFds(self.stdin_w, self.stdout_r, self.stderr_r)


@dataclass(frozen=True)
class ParentFds:
    """
    File descriptors pycloner must pass to the parent process.

    After passing them, the pycloner must call fds.close() to progress.
    """

    stdin_w: int
    stdout_r: int
    stderr_r: int

    def close(self) -> None:
        """
        Close these file descriptors.

        (Presumably, you copied them over a socket first.)
        """
        os.close(self.stdin_w)
        os.close(self.stdout_r)
        os.close(self.stderr_r)
