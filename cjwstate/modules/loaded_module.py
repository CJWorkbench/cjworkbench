from __future__ import annotations
from dataclasses import dataclass
import datetime
import logging
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional
from cjwkernel.errors import ModuleError
from cjwkernel.types import (
    ArrowTable,
    CompiledModule,
    FetchResult,
    Params,
    Tab,
    RenderResult,
)
from cjwkernel.kernel import ChrootContext
from cjwstate import minio
import cjwstate.modules.staticregistry
import cjwstate.modules


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedModule:
    """
    A module with `fetch()`, `migrate_params()` and `render()` methods.

    This object is stored entirely in memory. It does not hold references to
    database objects.
    """

    module_id_name: str
    version_sha1: str
    compiled_module: CompiledModule

    @property
    def name(self):
        return f"{self.module_id_name}:{self.version_sha1}"

    def render(
        self,
        *,
        chroot_context: ChrootContext,
        basedir: Path,
        input_table: ArrowTable,
        params: Params,
        tab: Tab,
        fetch_result: Optional[FetchResult],
        output_filename: str,
    ) -> RenderResult:
        """
        Process `table` with module `render` method, for a RenderResult.

        Raise ModuleError on error. (This is usually the module author's fault.)

        Log any ModuleError. Also log success.

        This synchronous method can be slow for complex modules or large
        datasets. Consider calling it from an executor.
        """
        time1 = time.time()
        begin_status_format = "%s.render() (%d rows, %d cols, %0.1fMB)"
        begin_status_args = (
            self.name,
            input_table.metadata.n_rows,
            len(input_table.metadata.columns),
            input_table.n_bytes_on_disk / 1024 / 1024,
        )
        logger.info(begin_status_format + " begin", *begin_status_args)
        status = "???"
        try:
            result = cjwstate.modules.kernel.render(
                self.compiled_module,
                chroot_context,
                basedir,
                input_table,
                params,
                tab,
                fetch_result,
                output_filename,
            )
            status = "(%drows, %dcols, %0.1fMB)" % (
                result.table.metadata.n_rows,
                len(result.table.metadata.columns),
                result.table.n_bytes_on_disk / 1024 / 1024,
            )
            return result
        except ModuleError as err:
            logger.exception("Exception in %s.render", self.module_id_name)
            status = type(err).__name__
            raise
        finally:
            time2 = time.time()

            logger.info(
                begin_status_format + " => %s in %dms",
                *begin_status_args,
                status,
                int((time2 - time1) * 1000),
            )

    def fetch(
        self,
        *,
        chroot_context: ChrootContext,
        basedir: Path,
        params: Params,
        secrets: Dict[str, Any],
        last_fetch_result: Optional[FetchResult],
        input_parquet_filename: Optional[str],
        output_filename: str,
    ) -> FetchResult:
        """
        Call module `fetch(...)` method to build a `FetchResult`.

        Raise ModuleError on error. (This is usually the module author's fault.)

        Log any ModuleError. Also log success.

        This synchronous method can be slow for complex modules, large datasets
        or slow network requests. Consider calling it from an executor.
        """
        time1 = time.time()
        status = "???"

        logger.info("%s.fetch() begin", self.name)

        try:
            ret = cjwstate.modules.kernel.fetch(
                self.compiled_module,
                chroot_context,
                basedir,
                params,
                secrets,
                last_fetch_result,
                input_parquet_filename,
                output_filename,
            )
            status = "%0.1fMB" % (ret.path.stat().st_size / 1024 / 1024)
            return ret
        except ModuleError as err:
            logger.exception("Exception in %s.fetch", self.module_id_name)
            status = type(err).__name__
            raise
        finally:
            time2 = time.time()
            logger.info(
                "%s.fetch() => %s in %dms",
                self.name,
                status,
                int((time2 - time1) * 1000),
            )

    def migrate_params(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call module `migrate_params()` to update maybe-stale `raw_params`.

        Raise ModuleError if module code did not execute.

        The result may not be valid. Call `param_schema.validate(result)` to
        raise `ValueError` on error; or call `param_schema.coerce(result)` to
        guarantee a valid result.

        Log any ModuleError. Also log success.
        """
        time1 = time.time()
        logger.info("%s.migrate_params() begin", self.name)
        status = "???"
        try:
            result = cjwstate.modules.kernel.migrate_params(
                self.compiled_module, raw_params
            )  # raise ModuleError
            status = "ok"
            return result
        except ModuleError as err:
            logger.exception("Exception in %s.migrate_params", self.module_id_name)
            status = type(err).__name__
            raise
        finally:
            time2 = time.time()
            logger.info(
                "%s.migrate_params() => %s in %dms",
                self.module_id_name,
                status,
                int((time2 - time1) * 1000),
            )

    @classmethod
    def for_module_version(
        cls, module_version: Optional["ModuleVersion"]
    ) -> Optional[LoadedModule]:
        """
        Return module referenced by `module_version`.

        If `module_version is None`, return `None`.

        Raise `FileNotFoundError` if module is not in minio.

        Raise `cjwkernel.errors.ModuleError` if module cannot be compiled.
        """
        if module_version is None:
            return None

        module_id_name = module_version.id_name
        version_sha1 = module_version.source_version_hash

        internal_modules = cjwstate.modules.staticregistry.Lookup
        if module_id_name in internal_modules:
            compiled_module = internal_modules[module_id_name]
        else:
            compiled_module = load_external_module(
                module_id_name, version_sha1, module_version.last_update_time
            )

        return cls(module_id_name, version_sha1, compiled_module)


def _is_basename_python_code(key: str) -> bool:
    """
    True iff the given filename is a module's Python code file.

    >>> _is_basename_python_code('filter.py')
    True
    >>> _is_basename_python_code('filter.json')  # not Python
    True
    >>> _is_basename_python_code('setup.py')  # setup.py is an exception
    False
    >>> _is_basename_python_code('test_filter.py')  # tests are exceptions
    False
    """
    if key == "setup.py":
        return False
    if key.startswith("test_"):
        return False
    return key.endswith(".py")


def _load_external_module_uncached(
    module_id_name: str, version_sha1: str
) -> CompiledModule:
    """
    Load a Python Module given a name and version.
    """
    prefix = "%s/%s/" % (module_id_name, version_sha1)
    all_keys = minio.list_file_keys(minio.ExternalModulesBucket, prefix)
    python_code_key = next(
        k for k in all_keys if _is_basename_python_code(k[len(prefix) :])
    )

    # Now we can load the code into memory.
    name = "%s.%s" % (module_id_name, version_sha1)
    with minio.temporarily_download(
        minio.ExternalModulesBucket, python_code_key
    ) as path:
        logger.info(f"Loading {name} from {path}")
        return cjwstate.modules.kernel.compile(path, name)


_load_external_module_lock = threading.Lock()


def load_external_module(
    module_id_name: str, version_sha1: str, last_update_time: datetime.datetime
) -> CompiledModule:
    """
    Load a Python Module given a name and version.

    Raise `FileNotFoundError` if module is not in minio.

    Raise `cjwkernel.errors.ModuleError` if module cannot be compiled.

    This function is thread-safe.

    This is memoized: for each module_id_name, the latest
    (version_sha1, last_update_time) is kept in memory to speed up future
    calls. (It's common during development for `version_sha1` to stay
    `develop`, though `last_update_time` changes frequently. We want to reload
    the module each time that happens.)

    Assume:

    * the files exist on disk and are valid
    * the files never change
    * the files' dependencies are in our PYTHONPATH
    * the files' dependencies haven't changed (i.e., its imports)

    ... in short: this function shouldn't raise an error.
    """
    cache = load_external_module._cache
    cache_condition = (version_sha1, last_update_time)

    # Quickly check if we can skip locking.
    cached_condition, cached_value = cache.get(module_id_name, (None, None))
    if cached_condition == cache_condition:
        return cached_value

    with _load_external_module_lock:
        cached_condition, cached_value = cache.get(module_id_name, (None, None))
        if cached_condition == cache_condition:
            return cached_value

        value = _load_external_module_uncached(module_id_name, version_sha1)
        cache[module_id_name] = (cache_condition, value)
        return value


load_external_module._cache = {}
load_external_module.cache_clear = load_external_module._cache.clear


def module_get_html_bytes(module_version: "ModuleVersion") -> Optional[bytes]:
    # Import staticmodules.registry only on demand. That way Django can
    # import all its objects without starting a (RAM-hungry) kernel.
    if module_version.id_name in cjwstate.modules.staticregistry.Lookup:
        return _internal_module_get_html_bytes(module_version.id_name)
    else:
        return _external_module_get_html_bytes(
            module_version.id_name, module_version.source_version_hash
        )


def _internal_module_get_html_bytes(id_name: str) -> Optional[bytes]:
    try:
        with open(
            Path(__file__).parent.parent.parent / "staticmodules" / f"{id_name}.html",
            "rb",
        ) as f:
            return f.read()
    except FileNotFoundError:
        return None


def _external_module_get_html_bytes(id_name: str, version: str) -> Optional[bytes]:
    prefix = "%s/%s/" % (id_name, version)
    all_keys = minio.list_file_keys(minio.ExternalModulesBucket, prefix)
    try:
        html_key = next(k for k in all_keys if k.endswith(".html"))
    except StopIteration:
        return None  # there is no HTML file

    return minio.get_object_with_data(minio.ExternalModulesBucket, html_key)["Body"]
