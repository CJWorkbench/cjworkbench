import contextlib
from dataclasses import dataclass, field
import io
import logging
import marshal
import os
from pathlib import Path
import selectors
import stat
import time
from typing import Any, ContextManager, Dict, List, Optional
import thrift.protocol.TBinaryProtocol
import thrift.transport.TTransport
from cjwkernel.forkserver import Forkserver
from cjwkernel.errors import ModuleCompileError, ModuleTimeoutError, ModuleExitedError
from cjwkernel.thrift import ttypes
from cjwkernel.types import (
    ArrowTable,
    CompiledModule,
    FetchResult,
    Params,
    RawParams,
    RenderResult,
    Tab,
)
from cjwkernel.util import tempdir_context
from cjwkernel.validate import validate


logger = logging.getLogger(__name__)


TIMEOUT = 600  # seconds
DEAD_PROCESS_N_WAITS = 50  # number of waitpid() calls after process exits
DEAD_PROCESS_WAIT_POLL_INTERVAL = 0.02  # seconds between waitpid() calls
LOG_BUFFER_MAX_BYTES = 100 * 1024  # waaaay too much log output
OUTPUT_BUFFER_MAX_BYTES = (
    2 * 1024 * 1024
)  # a huge migrate_params() return value, perhaps?


PARQUET_PATHS = [
    Path("/usr/bin/parquet-to-arrow"),
    Path("/usr/bin/parquet-to-arrow-slice"),
    Path("/usr/bin/parquet-to-text-stream"),
    Path("/usr/bin/parquet-diff"),
]


NETWORKING_PATHS = [
    # Path("/etc/ssl/certs/ca-certificates.crt"),
    Path("/etc/ssl/certs"),  # TODO narrow it down
    Path("/etc/ssl/openssl.cnf"),
    # Path("/usr/lib/ssl/openssl.cnf"),
    Path("/usr/lib/ssl/certs"),
    Path("/usr/share/ca-certificates"),
    Path("/etc/resolv.conf"),  # TODO sandbox DNS resolving
    Path("/etc/nsswitch.conf"),
]


DATA_PATHS = [Path("/usr/share/nltk_data")]


# Import all encodings. Some modules (e.g., loadurl) may encounter weird stuff
ENCODING_IMPORTS = [
    "encodings." + p.stem
    for p in Path("/usr/local/lib/python3.7/encodings").glob("*.py")
    if p.stem not in {"cp65001", "mbcs", "oem"}  # un-importable
]


@contextlib.contextmanager
def _chroot_dir_context(
    *, provide_paths: List[Path] = [], extract_paths: List[Path] = []
) -> ContextManager[Path]:
    """
    Prepare paths for forkserver's `chroot_dir` and `chroot_provide_paths`.

    Each of `provide_paths` is a file or directory we will expose to module
    code -- code with an effective UID/GID outside of 0-65535, so we can't
    transfer ownership to it. Each path within each `provide_path` will be
    temporarily set to other-readable. (TODO bind-mount instead of chroot,
    and somehow fiddle with ownership while mounting.)

    Each of `extract_paths` is an empty file that already exists, which we
    allow the module to write to. Each path will be set to world-writable
    within the chroot (so processes with effective UIDs outside of 0-65535 may
    write to it -- e.g., setuid-nonroot processes within forkserver's sandbox).
    After the context exits, the original permissions will be restored.

    The caller is expected to expose the `extract_path` through a
    `chroot_provide_paths` argument to forkserver. (For instance, if
    `extract_paths` includes /tmp/basedir/x.arrow, `chroot_provide_paths`
    should include /tmp/basedir or /tmp/basedir/x.arrow.

    TODO refactor chroot construction so it happens here, not in forkserver.
    The contents of the chroot really depend on the code being run -- in this
    case, code the kernel spawns.
    """
    with tempdir_context(prefix="kernel-chroot-") as chroot:
        chroot.chmod(0o755)

        old_stats: Dict[Path, os.stat_result] = {}

        for provide_path in provide_paths:
            for dirname, _, filenames in os.walk(provide_path):
                dirpath = Path(dirname)
                old_stat = dirpath.stat()
                old_stats[dirpath] = old_stat
                dirpath.chmod((old_stat.st_mode & 0o7777) | stat.S_IROTH | stat.S_IXOTH)
                for filename in filenames:
                    path = dirpath / filename
                    old_stat = path.stat()
                    old_stats[path] = old_stat
                    path.chmod((old_stat.st_mode & 0o7777) | stat.S_IROTH)

        for path in extract_paths:
            # read old_stat from cache, not from file! We changed the file.
            old_stat = old_stats[path]  # KeyError? provide_paths+extract_paths disagree
            # make it writable
            path.chmod((old_stat.st_mode & 0o7777) | stat.S_IROTH | stat.S_IWOTH)

        yield chroot

        for path in extract_paths:
            # The module ran as a high-UID user. Extract its output from
            # the chroot and give it its original permissions. That way,
            # future module runs won't be allowed to write it (unless
            # old_stats says it was world-writable in the first place).
            _extract_from_chroot(chroot, path)

        for path, old_stat in old_stats.items():
            # Restore original owner UID, GID
            os.chown(path, old_stat.st_uid, old_stat.st_gid)
            # Restore original permissions (ref: man inode(7))
            path.chmod(old_stat.st_mode & 0o7777)


def _extract_from_chroot(chroot: Path, path: Path) -> None:
    """
    Extract a file from `chroot`

    Modules write to files within their chroot. If path is `/tmp/out.arrow`,
    then the module wrote to `/chroot-dir/tmp/out.arrow`.

    (`path` exists before we create the chroot, and the chroot logic uses
    hard-link; so it's possible the module wrote directly to `/tmp/out.arrow`
    because `/chroot-dir/tmp/out.arrow` hard-links to it. But we don't count
    on modules opening an existing file rather than writing a new one.)

    To handle all cases, we hard-link `/tmp/out.arrow` to point to the file
    `/chroot-dir/tmp/out.arrow`. This "copies" the data, cheaply.
    
    The caller is responsible for restoring the file's permissions and
    attributes.

    Raise ModuleExitedError if the module tried to inject a symlink.
    """
    src = chroot / path.relative_to("/")
    if src.is_symlink():
        # If the module wrote a symlink, DO NOT READ IT. That's a security
        # issue -- the module could write "/etc/passwd" and then we'd read it.
        raise ModuleExitedError(0, "SECURITY: module output a symlink")
    path.unlink()  # os.link() won't overwrite; delete the destination
    os.link(src, path)


@dataclass
class ChildReader:
    fileno: int
    """
    File descriptor to read from.

    ChildReader won't call `os.close(fileno)` when closing; be sure
    you close `fileno` elsewhere.
    """

    limit_bytes: int
    bytesio: io.BytesIO = field(default_factory=io.BytesIO)
    overflowed: bool = False
    eof: bool = False

    def __post_init__(self):
        os.set_blocking(self.fileno, False)

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

    The solution: "forkserver". One "forkserver" process loads 100MB of Python
    deps and then idles. The "compile" method compiles a user's module, then
    forks and evaluates it in a child process to ensure sanity. The
    "migrate_params", "render" and "fetch" methods fork, evaluate the user's
    module, then invoke that user's `migrate_params()`, `render()` or `fetch`.

    Child processes cannot be trusted to return sane values. So we communicate
    via Thrift (which errors on unexpected data) rather than Python pickle
    (which executes code on unexpected data).
    """

    def __init__(
        self,
        validate_timeout: float = TIMEOUT,
        migrate_params_timeout: float = TIMEOUT,
        fetch_timeout: float = TIMEOUT,
        render_timeout: float = TIMEOUT,
    ):
        self.validate_timeout = validate_timeout
        self.migrate_params_timeout = migrate_params_timeout
        self.fetch_timeout = fetch_timeout
        self.render_timeout = render_timeout
        self._forkserver = Forkserver(
            module_main="cjwkernel.pandas.main.main",
            forkserver_preload=[
                "_strptime",
                "abc",
                "asyncio",
                "base64",
                "collections",
                "concurrent",
                "concurrent.futures",
                "concurrent.futures.thread",
                "dataclasses",
                "datetime",
                "enum",
                "functools",
                "inspect",
                "itertools",
                "json",
                "math",
                "multiprocessing",
                "multiprocessing.connection",
                "multiprocessing.popen_fork",
                "os.path",
                "re",
                "sqlite3",
                "ssl",
                "string",
                "typing",
                "urllib.parse",
                "warnings",
                "aiohttp",
                "bs4",
                "formulas",
                "formulas.parser",
                "html5lib",
                "html5lib.constants",
                "html5lib.filters",
                "html5lib.filters.whitespace",
                "html5lib.treewalkers.etree",
                "idna.uts46data",
                "lxml",
                "lxml.etree",
                "lxml.html",
                "lxml.html.html5parser",
                "networkx",
                "numpy",
                "nltk",
                "nltk.corpus",
                "nltk.sentiment.vader",
                "oauthlib",
                "oauthlib.oauth1",
                "oauthlib.oauth2",
                "pandas",
                "pandas.core",
                "pandas.core.apply",
                "pandas.core.computation.expressions",
                "pyarrow",
                "pyarrow.pandas_compat",
                "pyarrow.parquet",
                "re2",
                "requests",
                "schedula.dispatcher",
                "schedula.utils.blue",
                "schedula.utils.sol",
                "thrift.protocol.TBinaryProtocol",
                "thrift.transport.TTransport",
                "xlrd",
                "yajl",
                "cjwkernel.pandas.main",
                "cjwkernel.pandas.module",
                "cjwkernel.pandas.moduleutils",
                "cjwkernel.pandas.parse_util",
                "cjwkernel.parquet",
                *ENCODING_IMPORTS,
            ],
        )

    def __del__(self):
        self._forkserver.close()

    def compile(self, path: Path, module_slug: str) -> CompiledModule:
        """
        Detect common errors in the user's code.

        Raise ModuleCompileError, ModuleExitedError or ModuleTimeoutError on
        error.
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
        except SyntaxError as err:
            raise ModuleCompileError from err
        ret = CompiledModule(module_slug, marshal.dumps(code_object))
        self._validate(ret)
        return ret

    def _validate(self, compiled_module: CompiledModule) -> None:
        with _chroot_dir_context() as chroot:
            self._run_in_child(
                chroot=chroot,
                chroot_paths=DATA_PATHS,
                compiled_module=compiled_module,
                timeout=self.validate_timeout,
                result=ttypes.ValidateModuleResult(),
                function="validate_thrift",
                args=[],
            )

    def migrate_params(
        self, compiled_module: CompiledModule, params: Dict[str, Any]
    ) -> None:
        request = RawParams(params).to_thrift()
        with _chroot_dir_context() as chroot:
            response = self._run_in_child(
                chroot=chroot,
                chroot_paths=DATA_PATHS,
                compiled_module=compiled_module,
                timeout=self.migrate_params_timeout,
                result=ttypes.RawParams(),
                function="migrate_params_thrift",
                args=[request],
            )
        return RawParams.from_thrift(response).params

    def render(
        self,
        compiled_module: CompiledModule,
        basedir: Path,
        input_table: ArrowTable,
        params: Params,
        tab: Tab,
        fetch_result: Optional[FetchResult],
        output_filename: str,
    ) -> RenderResult:
        request = ttypes.RenderRequest(
            str(basedir),
            input_table.to_thrift(),
            params.to_thrift(),
            tab.to_thrift(),
            None if fetch_result is None else fetch_result.to_thrift(),
            output_filename,
        )
        with _chroot_dir_context(
            provide_paths=[basedir], extract_paths=[basedir / output_filename]
        ) as chroot:
            result = self._run_in_child(
                chroot=chroot,
                chroot_paths=[basedir]
                + DATA_PATHS
                + PARQUET_PATHS
                + NETWORKING_PATHS,  # TODO nix networking
                compiled_module=compiled_module,
                timeout=self.render_timeout,
                result=ttypes.RenderResult(),
                function="render_thrift",
                args=[request],
            )
            if result.table.filename and result.table.filename != output_filename:
                raise ModuleExitedError(0, "Module wrote to wrong output file")

        # RenderResult.from_thrift() verifies all filenames passed by the
        # module are in the directory the module has access to.
        render_result = RenderResult.from_thrift(result, basedir)
        if render_result.table.table is not None:
            validate(render_result.table.table, render_result.table.metadata)
        return render_result

    def fetch(
        self,
        compiled_module: CompiledModule,
        basedir: Path,
        params: Params,
        secrets: Dict[str, Any],
        last_fetch_result: Optional[FetchResult],
        input_parquet_filename: str,
        output_filename: str,
    ) -> FetchResult:
        request = ttypes.FetchRequest(
            str(basedir),
            params.to_thrift(),
            RawParams(secrets).to_thrift(),
            None if last_fetch_result is None else last_fetch_result.to_thrift(),
            input_parquet_filename,
            output_filename,
        )
        with _chroot_dir_context(
            provide_paths=[basedir], extract_paths=[basedir / output_filename]
        ) as chroot:
            result = self._run_in_child(
                chroot=chroot,
                chroot_paths=[basedir] + DATA_PATHS + PARQUET_PATHS + NETWORKING_PATHS,
                compiled_module=compiled_module,
                timeout=self.fetch_timeout,
                result=ttypes.FetchResult(),
                function="fetch_thrift",
                args=[request],
            )
            if result.filename and result.filename != output_filename:
                raise ModuleExitedError(0, "Module wrote to wrong output file")
        # TODO validate result isn't too large. If result is dataframe it makes
        # sense to truncate; but fetch results aren't necessarily data frames.
        # It's up to the module to enforce this logic ... but we need to set a
        # maximum file size.
        return FetchResult.from_thrift(result, basedir)

    def _run_in_child(
        self,
        *,
        chroot: Path,
        chroot_paths: List[Path],
        compiled_module: CompiledModule,
        timeout: float,
        result: Any,
        function: str,
        args: List[Any],
    ) -> None:
        """
        Fork a child process to run `function` with `args`.

        `args` must be Thrift data types. `result` must also be a Thrift type --
        its `.read()` function will be called, which may produce an error if
        the child process has a bug. (EOFError is very likely.)

        Raise ModuleExitedError if the child process did not behave as expected.

        Raise ModuleTimeoutError if it did not exit after a delay -- or if it
        closed its file descriptors long before it exited.
        """
        limit_time = time.time() + timeout

        module_process = self._forkserver.spawn_module(
            process_name=compiled_module.module_slug,
            chroot_dir=chroot,
            chroot_provide_paths=[(p, p) for p in chroot_paths],
            args=[compiled_module, function, args],
        )

        # stdout is Thrift package; stderr is logs
        output_reader = ChildReader(
            module_process.stdout.fileno(), OUTPUT_BUFFER_MAX_BYTES
        )
        log_reader = ChildReader(module_process.stderr.fileno(), LOG_BUFFER_MAX_BYTES)
        # Read until the child closes its stdout and stderr
        with selectors.DefaultSelector() as selector:
            selector.register(output_reader.fileno, selectors.EVENT_READ)
            selector.register(log_reader.fileno, selectors.EVENT_READ)

            timed_out = False
            while selector.get_map():
                remaining = limit_time - time.time()
                if remaining <= 0:
                    if not timed_out:
                        timed_out = True
                        module_process.kill()  # untrusted code could ignore SIGTERM
                    timeout = None  # wait as long as it takes for everything to die
                    # Fall through. After SIGKILL the child will close each fd,
                    # sending EOF to us. That means the selector _must_ return.
                else:
                    timeout = remaining  # wait until we reach our timeout

                events = selector.select(timeout=timeout)
                ready = frozenset(key.fd for key, _ in events)
                for reader in (output_reader, log_reader):
                    if reader.fileno in ready:
                        reader.ingest()
                        if reader.eof:
                            selector.unregister(reader.fileno)

        # The child closed its fds, so it should die soon. If it doesn't, that's
        # a bug -- so kill -9 it!
        #
        # os.wait() has no timeout option, and asyncio messes with signals so
        # we won't use those. Spin until the process dies, and force-kill if we
        # spin too long.
        for _ in range(DEAD_PROCESS_N_WAITS):
            pid, exit_status = module_process.wait(os.WNOHANG)
            if pid != 0:  # pid==0 means process is still running
                break
            time.sleep(DEAD_PROCESS_WAIT_POLL_INTERVAL)
        else:
            # we waited and waited. No luck. Dead module. Kill it.
            timed_out = True
            module_process.kill()
            _, exit_status = module_process.wait(0)
        if os.WIFEXITED(exit_status):
            exit_code = os.WEXITSTATUS(exit_status)
        elif os.WIFSIGNALED(exit_status):
            exit_code = -os.WTERMSIG(exit_status)
        else:
            raise RuntimeError("Unhandled wait() status: %r" % exit_status)

        if timed_out:
            raise ModuleTimeoutError

        if exit_code != 0:
            raise ModuleExitedError(exit_code, log_reader.to_str())

        transport = thrift.transport.TTransport.TMemoryBuffer(output_reader.buffer)
        protocol = thrift.protocol.TBinaryProtocol.TBinaryProtocol(transport)
        try:
            result.read(protocol)
        except EOFError:  # TODO handle other errors Thrift may throw
            raise ModuleExitedError(exit_code, log_reader.to_str()) from None

        # We should be at the end of the output now. If we aren't, that means
        # the child wrote too much.
        if transport.read(1) != b"":
            raise ModuleExitedError(exit_code, log_reader.to_str())

        if log_reader.buffer:
            logger.info("Output from module process: %s", log_reader.to_str())

        return result
