import array
import ctypes
import os
import sys
import socket
import cjwkernel.pandas.main
from . import protocol


libc = ctypes.CDLL("libc.so.6")
PR_SET_NAME = 15


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

            # Rewrite sys.stdout+sys.stderr to write to log_fd
            #
            # We're writing in text mode so we're forced to buffer output. But
            # we don't want buffering: if we crash, we want whatever we write
            # to be visible to the reader at the other end, even if we crash.
            # Set buffering=1, meaning "line buffering". This is what
            # interactive Python uses for stdout+stderr.
            sys.stdout = os.fdopen(message.log_fd, "wt", encoding="utf-8", buffering=1)
            sys.stderr = sys.stdout
            sys.__stdout__ = sys.stdout
            sys.__stderr__ = sys.stderr

            # Aid in debugging a bit
            name = "cjwkernel-module:%s" % message.compiled_module.module_slug
            libc.prctl(PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)

            # Run the module code. This is what it's all about!
            #
            # If the module raises an exception, that's okay -- the
            # forkserver_main() loop won't catch them so they'll crash this
            # "module" process and log output to "log_fd" -- exactly what we
            # want.
            cjwkernel.pandas.main.main(
                message.compiled_module,
                message.output_fd,
                message.function,
                *message.args,
            )  # may raise ... er ... anything

            # SECURITY: the module code may have rewritten our stack, our
            # code ... anything. We _want_ to os._exit(0) so as to close
            # the file descriptors "parent" is reading and then let
            # "parent" reap us. But there are no guarantees. A malicious
            # process could find a way to jump somewhere else instead of
            # exiting.
            #
            # That's okay: we closed all the interesting file descriptors;
            # we sandboxed the process; and "parent" has a timer running
            # that will kill the "module" process.
            #
            # But in the _common_ case ... exit here.
            os._exit(0)
        else:
            # "spawner"
            # Send "module_pid" to "forkserver". We can't send it to "parent"
            # because we haven't died yet; and "parent" won't be able to wait
            # on it until after we've died. (Only "forkserver" knows when
            # "spawner" has died.)
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
        "parent" having PR_SET_CHILD_SUBREAPER.
    5a. Parent receives PID from client.
    6a. Parent UNLOCKs
    7a. Parent reads from its fds and polls PID.

    For shutdown, the client simply closes its connection.

    The inevitable race: if "parent" doesn't read "module_pid" from the other
    end of "sock" and wait() for it, then nothing will wait() for the module
    process after it dies and it will become a zombie.
    """
    # 1b. Child establishes socket connection
    #
    # Note: we don't put this in a `with` block, because that would add a
    # finalizer. Finalizers will run in the "module_pid" process if
    # cjwkernel.pandas.main() raises an exception ... but the "module_pid"
    # process closes the socket before calling cjwkernel.pandas.main(), so the
    # finalizer would crash.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, fileno=socket_fd)

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
