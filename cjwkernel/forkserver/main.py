import array
import ctypes
import os
import sys
import socket
import cjwkernel.pandas.main
from typing import Any, List
from . import protocol


libc = ctypes.CDLL("libc.so.6")
PR_SET_NAME = 15
PR_SET_CHILD_SUBREAPER = 36


def spawn_module(
    ppid: int, sock: socket.socket, message: protocol.SpawnPandasModule
) -> protocol.SpawnedPandasModule:
    """
    Double-fork (to make `ppid` our parent); send PID on `sock`.

    This closes all open file descriptors in the child: stdin, stdout, stderr,
    and `sock.fileno()`. The reason is SECURITY: the child will invoke
    user-provided code, so we bar everything it doesn't need. (Heck, it doesn't
    even get stdin+stdout+stderr!)

    There are four processes running concurrently here:

    * "parent" (`ppid`): the Python process that holds a ForkServer handle.
                         It sent `SpawnPandasModule` on `sock` and expects a
                         response of `SpawnedPandasModule` (with "module" PID).
    * "forkserver": the forkserver_main() process. It called this function. It
                    has few file handles open -- by design. It spawns
                    "spawner", reads "module_pid", and then returns
                    "module_pid".
    * "spawner": a child we will launch, to double-fork. Its mission: fork
                 "module" with a fake init process of `ppid`, send the "module"
                 PID to "forkserver", then die.
    * "module": invokes `cjwkernel.pandas.main.main()`, using the file
                descriptors passed in `SpawnPandasModule`.

    The "spawner" child (the part of the double-fork that dies right away) will
    send the final PID over `sock`, then exit. After it exits, "forkserver"
    will reap it and return.
    """
    module_pid_r, module_pid_w = os.pipe()
    spawner_pid = os.fork()
    if spawner_pid == 0:
        # "spawner" (child)
        os.close(module_pid_r)
        os.close(sock.fileno())

        module_pid = os.fork()
        if module_pid == 0:
            # "module" (subchild)
            # Close everything we don't want module code to access.
            os.close(module_pid_w)
            os.close(sys.stdin.fileno())
            os.close(sys.stdout.fileno())  # disallow flooding our logs
            os.close(sys.stderr.fileno())  # disallow flooding our logs

            # Aid in debugging a bit
            name = "cjwkernel-module:%s" % message.compiled_module.module_slug
            libc.prctl(PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)

            # Run the module code. This is what it's all about!
            cjwkernel.pandas.main.main(
                message.compiled_module,
                message.output_fd,
                message.log_fd,
                message.function,
                *message.args
            )
            # SECURITY: the module code may have rewritten anything here. We
            # _want_ to os._exit(0) so as to close the file descriptors
            # "parent" is reading and then let "parent" reap us. But there are
            # no guarantees. A malicious process could find a way to jump to
            # some other code and read other memory.
            #
            # ... good thing we closed all the interesting file descriptors!
            os._exit(0)
        else:
            # "spawner"

            # Make "parent" the parent of "spawner" once "spawner" dies. After
            # "spawner" dies, "parent" may waitpid(module_pid).
            #
            # The inevitable race: if "parent" doesn't read "module_pid" from
            # the other end of "sock" and wait() for it, then nothing will
            # wait() for the module process after it dies and it will become a
            # zombie.
            libc.prctl(PR_SET_CHILD_SUBREAPER, ppid, 0, 0, 0)

            os.write(module_pid_w, array.array("i", [module_pid]).tobytes())
            os._exit(0)  # closes all open fds
    else:
        # "forkserver"

        # Wait for "spawner" to tell us the module_pid.
        # Assume we'll read all bytes from module_pid_r in a single syscall.
        module_pid_arr = array.array("i")
        module_pid_arr.frombytes(os.read(module_pid_r, module_pid_arr.itemsize))
        module_pid = module_pid_arr[0]
        os.close(module_pid_r)

        # Now wait for "spawner" to die. "parent" can only wait for "module"
        # once "parent" is its parent -- which only happens after "spawner"
        # dies.
        _, exit_code = os.waitpid(spawner_pid, 0)
        if exit_code != 0:
            raise RuntimeError(
                "Spawner %d exited with code %d (expected 0)", (spawner_pid, exit_code)
            )

        # Send module_pid to "parent" and then exit. After we exit, the
        # "module" process will be reparented to "parent".
        protocol.SpawnedPandasModule(module_pid).send_on_socket(sock)


def forkserver_main(ppid: int, socket_fd: int) -> None:
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
        PR_SET_CHILD_SUBREAPER.
    5a. Parent receives PID from client.
    6a. Parent UNLOCKs
    7a. Parent reads from its fds and polls PID.

    For shutdown, the client simply closes its connection.
    """
    # 1b. Child establishes socket connection
    with socket.fromfd(socket_fd, socket.AF_INET, socket.SOCK_STREAM) as sock:
        assert sock.fileno() != socket_fd  # socket.fromfd() does a dup...
        os.close(socket_fd)  # ... so close the original.

        # 2b. Child imports modules in its main (and only) thread
        imports = protocol.ImportModules.recv_on_socket(sock)
        for im in imports.modules:
            __import__(im)

        while True:
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
            spawn_module(ppid, sock, message)

            os.close(message.output_fd)
            os.close(message.log_fd)
