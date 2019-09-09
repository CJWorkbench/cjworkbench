from __future__ import annotations
from dataclasses import dataclass
import datetime
import logging
from pathlib import Path
import time
from typing import Any, Dict, Optional
from cjworkbench.sync import database_sync_to_async
from cjwkernel.errors import ModuleError
from cjwkernel.types import (
    ArrowTable,
    CompiledModule,
    FetchResult,
    I18nMessage,
    Params,
    Tab,
    RenderError,
    RenderResult,
)
from cjwkernel.param_dtype import ParamDTypeDict
from cjwstate import minio
from . import module_loader
from .module_version import ModuleVersion
from server.modules import Lookup as InternalModules


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
    param_schema: ParamDTypeDict
    compiled_module: CompiledModule

    @property
    def name(self):
        return f"{self.module_id_name}:{self.version_sha1}"

    def render(
        self,
        input_table: ArrowTable,
        params: Params,
        tab: Tab,
        fetch_result: Optional[FetchResult],
        output_path: Path,
    ) -> RenderResult:
        """
        Process `table` with module `render` method, for a RenderResult.

        Exceptions become error results. This method cannot raise an exception.
        (It is always an error for module code to raise an exception.)

        This synchronous method can be slow for complex modules or large
        datasets. Consider calling it from an executor.
        """
        time1 = time.time()
        try:
            result = module_loader.kernel.render(
                self.compiled_module,
                input_table,
                params,
                tab,
                fetch_result,
                output_path,
            )
        except ModuleError as err:
            logger.exception("Exception in %s.render", self.module_id_name)
            result = RenderResult(
                errors=[
                    RenderError(
                        I18nMessage(
                            "TODO_i18n",
                            [
                                "Something unexpected happened. We have been notified and are "
                                "working to fix it. If this persists, contact us. Error code: "
                                + str(err)
                            ],
                        )
                    )
                ]
            )
        time2 = time.time()

        logger.info(
            "%s.render(%drows, %dcols, %0.1fMB) => (%drows, %dcols, %0.1fMB) in %dms",
            self.name,
            input_table.metadata.n_rows,
            len(input_table.metadata.columns),
            input_table.n_bytes_on_disk / 1024 / 1024,
            result.table.metadata.n_rows,
            len(result.table.metadata.columns),
            result.table.n_bytes_on_disk / 1024 / 1024,
            int((time2 - time1) * 1000),
        )

        return result

    def fetch(
        self,
        *,
        params: Params,
        secrets: Dict[str, Any],
        last_fetch_result: Optional[FetchResult],
        input_table: ArrowTable,
        output_path: Path,
    ) -> FetchResult:
        """
        Call module `fetch(...)` method to build a `FetchResult`.

        Exceptions become error results. This method cannot raise an exception.
        (It is always an error for module code to raise an exception.)

        This synchronous method can be slow for complex modules, large datasets
        or slow network requests. Consider calling it from an executor.
        """
        time1 = time.time()
        try:
            result = module_loader.kernel.fetch(
                self.compiled_module,
                params,
                secrets,
                last_fetch_result,
                input_table,
                output_path,
            )
        except ModuleError as err:
            logger.exception("Exception in %s.fetch", self.module_id_name)
            result = FetchResult(
                path=output_path,
                errors=[
                    RenderError(
                        I18nMessage(
                            "TODO_i18n",
                            [
                                "Something unexpected happened. We have been notified and are "
                                "working to fix it. If this persists, contact us. Error code: "
                                + str(err)
                            ],
                        )
                    )
                ],
            )

        time2 = time.time()
        logger.info(
            "%s.fetch => %0.1fMB in %dms",
            self.name,
            result.path.stat().st_size / 1024 / 1024,
            int((time2 - time1) * 1000),
        )

        return result

    def migrate_params(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call module `migrate_params()` to update maybe-stale `raw_params`.

        Raise ModuleError if module code did not execute.

        Raise ValueError if module code returned params that do not match spec.
        """
        time1 = time.time()
        try:
            values = module_loader.kernel.migrate_params(
                self.compiled_module, raw_params
            )  # raise ModuleError
            try:
                self.param_schema.validate(values)
            except ValueError as err:
                raise ValueError(
                    "%s.migrate_params() gave bad output: %s"
                    % (self.module_id_name, str(err))
                )
            return values
        finally:
            time2 = time.time()
            logger.info(
                "%s.migrate_params() in %dms",
                self.module_id_name,
                int((time2 - time1) * 1000),
            )

    @classmethod
    @database_sync_to_async
    def for_module_version(
        cls, module_version: Optional[ModuleVersion]
    ) -> Optional[LoadedModule]:
        """
        Return module referenced by `module_version` (asynchronously).

        If `module_version is None`, return `None`.

        We assume:

        * the ModuleVersion and Module are in the database (foreign keys prove
          this)
        * external-module files exist on disk
        * external-module files were validated before being written to database
        * external-module files haven't changed
        * external-module files' dependencies are in PYTHONPATH
        * external-module files' dependencies haven't changed (i.e., imports)

        Invalid assumption? Fix the bug elsewhere.
        """
        return cls.for_module_version_sync(module_version)

    @classmethod
    def for_module_version_sync(
        cls, module_version: Optional[ModuleVersion]
    ) -> Optional[LoadedModule]:
        """
        Return module referenced by `module_version`.

        We assume:

        * if `module_version is not None`, then its `module` is in the database
        * external-module files exist on disk
        * external-module files were validated before being written to database
        * external-module files haven't changed
        * external-module files' dependencies are in PYTHONPATH
        * external-module files' dependencies haven't changed (i.e., imports)

        Invalid assumption? Fix the bug elsewhere.

        Do not call this from an async method, because you may leak a database
        connection. Use `for_module_version` instead.
        """
        if module_version is None:
            return None

        module_id_name = module_version.id_name
        version_sha1 = module_version.source_version_hash

        try:
            compiled_module = InternalModules[module_id_name]
            version_sha1 = "internal"
        except KeyError:
            compiled_module = load_external_module(
                module_id_name, version_sha1, module_version.last_update_time
            )

        param_schema = module_version.param_schema

        return cls(module_id_name, version_sha1, param_schema, compiled_module)


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
        return module_loader.kernel.compile(path, name)


def load_external_module(
    module_id_name: str, version_sha1: str, last_update_time: datetime.datetime
) -> CompiledModule:
    """
    Load a Python Module given a name and version.

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
    cached_condition, cached_value = cache.get(module_id_name, (None, None))

    if cached_condition == cache_condition:
        return cached_value

    value = _load_external_module_uncached(module_id_name, version_sha1)
    cache[module_id_name] = (cache_condition, value)
    return value


load_external_module._cache = {}
load_external_module.cache_clear = load_external_module._cache.clear


def module_get_html_bytes(module_version: ModuleVersion) -> Optional[bytes]:
    if module_version.id_name in InternalModules:
        return _internal_module_get_html_bytes(module_version.id_name)
    else:
        return _external_module_get_html_bytes(
            module_version.id_name, module_version.source_version_hash
        )


def _internal_module_get_html_bytes(id_name: str) -> Optional[bytes]:
    try:
        with open(
            Path(__file__).parent.parent / "modules" / f"{id_name}.html", "rb"
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
