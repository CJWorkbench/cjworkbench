from dataclasses import dataclass, field
import io
import logging
import marshal
import multiprocessing
import os
from pathlib import Path
import selectors
import time
from typing import Any, Dict, Optional
import thrift.protocol
import thrift.transport
from cjwkernel.errors import ModuleCompileError, ModuleTimeoutError, ModuleExitedError
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    ArrowTable,
    CompiledModule,
    FetchResult,
    Params,
    RenderResult,
    Tab,
    TabOutput,
)
from cjwkernel.pandas.main import main


logger = logging.getLogger(__name__)


TIMEOUT = 30  # seconds
LOG_BUFFER_MAX_BYTES = 100 * 1024  # waaaay too much log output
OUTPUT_BUFFER_MAX_BYTES = (
    2 * 1024 * 1024
)  # a huge migrate_params() return value, perhaps?


@dataclass
class ChildReader:
    fileno: int
    """
    File descriptor to read from. Must be non-blocking.
    """

    limit_bytes: int
    bytesio: io.BytesIO = field(default_factory=io.BytesIO)
    overflowed: bool = False
    eof: bool = False

    def ingest(self):
        if self.eof:
            return
        allowed = self.limit_bytes - len(self.buffer)
        while allowed > 0:
            try:
                b = os.read(self.fileno, allowed)
            except BlockingIOError:
                return  # that's all for now
            if not b:
                self.eof = True
                return  # EOF
            self.bytesio.write(b)
            allowed -= len(b)
        # Detect overflow by reading one more byte
        if not self.overflowed:
            try:
                b = os.read(self.fileno, 1)
            except BlockingIOError:
                return
            if b:
                self.overflowed = True
            else:
                self.eof = True
        # Read all overflowed data (and ignore it), so the program does not
        # stall because a buffer is full
        if self.overflowed:
            while True:
                try:
                    b = os.read(self.fileno, 50 * 1024)
                except BlockingIOError:
                    return  # that's all for now
                if not b:
                    self.eof = True
                    return  # EOF

    @property
    def buffer(self):
        return self.bytesio.getbuffer()

    def to_str(self) -> str:
        return str(self.buffer, encoding="utf-8", errors="replace")


class Kernel:
    """
    Compiles and runs user-supplied module code.

    Here's the thing about user code: it can only be run in a sandbox.
    `compile()` is safe, but `exec()` is dangerous -- after running user code,
    the entire process must be killed: otherwise, the module may leak one
    workflow's data into another workflow (intentionally or not).

    The solution: Python's multiprocessing "forkserver". One "forkserver"
    process loads 100MB of Python deps and then idles. The "compile" method
    compiles a user's module, then forks and evaluates it in a child process to ensure
    sanity. The "migrate_params", "render" and "fetch" methods fork, evaluate
    the user's module, then invoke that user's `migrate_params()`, `render()`
    or `fetch`.

    Child processes cannot be trusted to use the regular `multiprocessing.Pipe`
    `send()` and `recv()`, because they use Python pickle, which can inject
    code. So we communicate via Thrift.
    """

    def __init__(self):
        self._context = multiprocessing.get_context("forkserver")
        self._context.set_forkserver_preload(
            ["cjwkernel.thrift.KernelModule", "pandas", "pyarrow", "numpy", "nltk"]
        )

    def compile(self, path: Path, module_slug: str) -> CompiledModule:
        """
        Detect common errors in the user's code.

        Raise CompileError, 
        """
        code = path.read_text()
        try:
            code_object = compile(
                code,
                filename=f"{module_slug}.py",
                mode="exec",
                dont_inherit=True,
                optimize=0,  # keep assertions -- we use them!
            )
        except SyntaxError:
            raise ModuleCompileError  # and SyntaxError is its cause
        ret = CompiledModule(module_slug, marshal.dumps(code_object))
        self._validate(ret)
        return ret

    def _validate(self, compiled_module: CompiledModule) -> None:
        self._run_in_child(
            compiled_module, ttypes.ValidateModuleResult(), "validate_thrift"
        )

    def migrate_params(
        self, compiled_module: CompiledModule, params: Dict[str, Any]
    ) -> None:
        request = Params(params).to_thrift()
        response = self._run_in_child(
            compiled_module, ttypes.Params(), "migrate_params_thrift", request
        )
        return Params.from_thrift(response).params

    def render(
        self,
        compiled_module: CompiledModule,
        input_table: ArrowTable,
        params: Dict[str, Any],
        tab: Tab,
        input_tabs: Dict[str, TabOutput],
        fetch_result: Optional[FetchResult],
    ) -> RenderResult:
        request = ttypes.RenderRequest(
            input_table.to_thrift(),
            Params(params).to_thrift(),
            tab.to_thrift(),
            {k: v.to_thrift() for k, v in input_tabs.items()},
            None if fetch_result is None else fetch_result.to_thrift(),
        )
        result = self._run_in_child(
            compiled_module, ttypes.RenderResult(), "render_thrift", request
        )
        return RenderResult.from_thrift(result)

    def _run_in_child(
        self, compiled_module: CompiledModule, result: Any, function: str, *args
    ) -> None:
        """
        Fork a child process to run `function` with `args`.

        `args` must be Thrift data types. `result` must also be a Thrift type --
        its `.read()` function will be called, which may produce an error if
        the child process has a bug. (EOFError is very likely.)

        Raise ModuleExitedError if the child process did not behave as expected.
        Raise ModuleTimeoutError if it did not exit after a delay.
        """

        output_r, output_w = os.pipe()
        os.set_inheritable(output_w, True)
        os.set_blocking(output_r, False)
        output_reader = ChildReader(output_r, OUTPUT_BUFFER_MAX_BYTES)
        log_r, log_w = os.pipe()
        log_reader = ChildReader(log_r, LOG_BUFFER_MAX_BYTES)
        os.set_inheritable(log_w, True)
        os.set_blocking(log_r, False)

        child = self._context.Process(
            target=main,
            args=[
                compiled_module,
                # Python's multiprocessing module is a bit more complex than
                # C fork(). File descriptors get mangled during fork. So we
                # pass them as callbacks.
                self._context.reducer.DupFd(output_w),
                self._context.reducer.DupFd(log_w),
                function,
                *args,
            ],
            name="cjwkernel-module:%s" % compiled_module.module_slug,
        )
        selector = selectors.DefaultSelector()
        child.start()
        os.close(output_w)
        os.close(log_w)
        selector.register(log_r, selectors.EVENT_READ)
        selector.register(output_r, selectors.EVENT_READ)
        selector.register(child.sentinel, selectors.EVENT_READ)
        # starting here, `child` can't be trusted. In particular,
        # DO NOT call `log_receiver.recv()` or `output_receiver.recv()`!!!
        # `recv()` is evil.
        start_time = time.time()
        timed_out = False
        while True:
            remaining = time.time() - start_time
            if remaining <= 0:
                if not timed_out:
                    timed_out = True
                    child.kill()  # untrusted code will never die without SIGKILL
                timeout = None  # wait as long as it takes for everything to die
            else:
                timeout = remaining  # wait until we reach our timeout
            events = selector.select(timeout=timeout)
            ready = frozenset(key.fd for key, _ in events)
            for reader in (output_reader, log_reader):
                if reader.fileno in ready:
                    reader.ingest()
                    if reader.eof:
                        selector.unregister(reader.fileno)
            if child.sentinel in ready:
                timed_out = False
                break  # child has exited
        # Now that the child has exited, read from the child until EOF. We know
        # EOF is coming, because the child died.
        for reader in (output_reader, log_reader):
            if not reader.eof:
                os.set_blocking(reader.fileno, True)
                reader.ingest()
        # ... and reap the child
        selector.close()
        child.join()

        if timed_out:
            raise ModuleTimeoutError

        if child.exitcode != 0:
            raise ModuleExitedError(child.exitcode, log_reader.to_str())

        transport = thrift.transport.TTransport.TMemoryBuffer(output_reader.buffer)
        protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)
        try:
            result.read(protocol)
        except EOFError:  # TODO handle other errors Thrift may throw
            raise ModuleExitedError(child.exitcode, log_reader.to_str())

        # We should be at the end of the output now. If we aren't, that means
        # the child wrote too much.
        if transport.read(1) != b"":
            raise ModuleExitedError(child.exitcode, log_reader.to_str())

        if log_reader.buffer:
            logger.info("Output from child:" % log_reader.to_str())

        return result
