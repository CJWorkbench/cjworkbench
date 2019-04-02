import asyncio
import datetime
from functools import partial
import inspect
import logging
import os
from pathlib import Path
import sys
import time
import traceback
from types import ModuleType
from typing import Any, Awaitable, Callable, Dict, Optional
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
import pandas as pd
from cjworkbench.types import ProcessResult, RenderColumn
from . import module_loader
from .module_version import ModuleVersion
from .Params import Params
from .param_field import ParamDTypeDict
from ..modules import Lookup as InternalModules
from server import minio


logger = logging.getLogger(__name__)


def _default_render(table, params,
                    *, fetch_result, **kwargs) -> ProcessResult:
    """Render fetch_result or pass-through input."""
    if fetch_result is not None:
        return fetch_result
    else:
        return ProcessResult(table)


async def _default_fetch(params, **kwargs) -> Optional[ProcessResult]:
    """No-op fetch."""
    return None


class DeletedModule:
    def render(self, table: Optional[pd.DataFrame], params: Params,
               tab_name: str,
               fetch_result: Optional[ProcessResult]) -> ProcessResult:
        logger.info('render() deleted module')
        return ProcessResult(error='Cannot render: module was deleted')

    async def fetch(
        self,
        params: Params,
        *,
        workflow_id: int,
        get_input_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_stored_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_workflow_owner: Callable[[], Awaitable[User]]
    ) -> ProcessResult:
        logger.info('fetch() deleted module')
        return ProcessResult(error='Cannot fetch: module was deleted')


class LoadedModule:
    """A module with `fetch` and `render` methods.
    """
    def __init__(self, module_id_name: str, version_sha1: str,
                 render_impl: Callable = _default_render,
                 fetch_impl: Callable = _default_fetch,
                 migrate_params_impl: Optional[Callable] = None):
        self.module_id_name = module_id_name
        self.version_sha1 = version_sha1
        self.name = f'{module_id_name}:{version_sha1}'
        self.render_impl = render_impl
        self.fetch_impl = fetch_impl
        self.migrate_params_impl = migrate_params_impl

    def _wrap_exception(self, err) -> ProcessResult:
        """Coerce an Exception (must be on the stack) into a ProcessResult."""
        # Catch exceptions in the module render function, and return
        # error message + line number to user
        exc_name = type(err).__name__
        exc_type, exc_obj, exc_tb = sys.exc_info()
        # [1] = where the exception ocurred, not the render()
        tb = traceback.extract_tb(exc_tb)[1]
        fname = os.path.split(tb[0])[1]
        lineno = tb[1]

        error = f'{exc_name}: {str(err)} at line {lineno} of {fname}'
        return ProcessResult(error=error)

    def render(self, input_result: Optional[ProcessResult],
               params: Dict[str, Any], tab_name: str,
               fetch_result: Optional[ProcessResult]) -> ProcessResult:
        """
        Process `table` with module `render` method, for a ProcessResult.

        If the `render` method raises an exception, this method will return an
        error string. It is always an error for a module to raise an exception.

        Exceptions become error messages. This method cannot produce an
        exception.

        This synchronous method can be slow for complex modules or large
        datasets. Consider calling it from an executor.
        """
        kwargs = {}
        spec = inspect.getfullargspec(self.render_impl)
        varkw = bool(spec.varkw)  # if True, function accepts **kwargs
        kwonlyargs = spec.kwonlyargs
        if varkw or 'fetch_result' in kwonlyargs:
            kwargs['fetch_result'] = fetch_result
        if varkw or 'tab_name' in kwonlyargs:
            kwargs['tab_name'] = tab_name
        if varkw or 'input_columns' in kwonlyargs:
            kwargs['input_columns'] = dict(
                (c.name, RenderColumn(c.name, c.type.name,
                                      getattr(c.type, 'format', None)))
                for c in input_result.table_shape.columns
            )

        table = input_result.dataframe

        time1 = time.time()

        try:
            out = self.render_impl(table, params, **kwargs)
        except Exception as err:
            logger.exception('Exception in %s.render', self.module_id_name)
            out = self._wrap_exception(err)

        try:
            out = ProcessResult.coerce(out)
        except Exception as err:
            logger.exception('Exception coercing %s.render output',
                             self.module_id_name)
            out = self._wrap_exception(err)

        out.truncate_in_place_if_too_big()
        out.sanitize_in_place()

        time2 = time.time()
        shape = out.dataframe.shape if out is not None else (-1, -1)
        logger.info('%s rendered (%drows,%dcols)=>(%drows,%dcols) in %dms',
                    self.name, table.shape[0], table.shape[1],
                    shape[0], shape[1], int((time2 - time1) * 1000))

        return out

    async def fetch(
        self,
        params: Params,
        *,
        workflow_id: int,
        get_input_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_stored_dataframe: Callable[[], Awaitable[pd.DataFrame]],
        get_workflow_owner: Callable[[], Awaitable[User]]
    ) -> ProcessResult:
        """
        Process `params` with module `fetch` method, to build a ProcessResult.

        If the `fetch` method raises an exception, this method will return an
        error string. It is always an error for a module to raise an exception.
        """
        kwargs = {}
        spec = inspect.getfullargspec(self.fetch_impl)
        varkw = bool(spec.varkw)  # if True, function accepts **kwargs
        kwonlyargs = spec.kwonlyargs
        if varkw or 'workflow_id' in kwonlyargs:
            kwargs['workflow_id'] = workflow_id
        if varkw or 'get_input_dataframe' in kwonlyargs:
            kwargs['get_input_dataframe'] = get_input_dataframe
        if varkw or 'get_stored_dataframe' in kwonlyargs:
            kwargs['get_stored_dataframe'] = get_stored_dataframe
        if varkw or 'get_workflow_owner' in kwonlyargs:
            kwargs['get_workflow_owner'] = get_workflow_owner

        # Pass input to params.to_painful_dict().
        #
        # TODO consider ... _not_ doing this. It's only needed if the module
        # has 'column' params ... which [2019-01-31, adamhooper] is unwise. We
        # use it in old-style 'join' and 'concat' (which require fetch of
        # another workflow) and in 'urlscraper' (which seems like a unique
        # case).

        input_dataframe_future = get_input_dataframe()

        input_dataframe = await input_dataframe_future
        if input_dataframe is None:
            input_dataframe = pd.DataFrame()
        params = params.to_painful_dict(input_dataframe)

        # If we're passing get_input_dataframe via kwargs, short-circuit it
        # because we already know the result.
        async def get_input_dataframe_again():
            return input_dataframe
        if 'get_input_dataframe' in kwargs:
            kwargs['get_input_dataframe'] = get_input_dataframe_again

        time1 = time.time()

        if inspect.iscoroutinefunction(self.fetch_impl):
            future_result = self.fetch_impl(params, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            func = partial(self.fetch_impl, params, **kwargs)
            future_result = loop.run_in_executor(None, func)

        try:
            out = await future_result
        except Exception as err:
            logger.exception('Exception in %s.fetch', self.module_id_name)
            out = self._wrap_exception(err)

        time2 = time.time()

        if out is None:
            shape = (-1, -1)
        else:
            out = ProcessResult.coerce(out)
            out.truncate_in_place_if_too_big()
            out.sanitize_in_place()
            shape = out.dataframe.shape

        logger.info('%s fetched =>(%drows,%dcols) in %dms',
                    self.name, shape[0], shape[1],
                    int((time2 - time1) * 1000))

        return out

    @classmethod
    @database_sync_to_async
    def for_module_version(cls,
                           module_version: ModuleVersion) -> 'LoadedModule':
        """
        Return module referenced by `module_version` (asynchronously).

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

    def migrate_params(self, schema: ParamDTypeDict,
                       values: Dict[str, Any]) -> Dict[str, Any]:
        if self.migrate_params_impl is not None:
            try:
                values = self.migrate_params_impl(values)
            except Exception as err:
                raise ValueError('%s.migrate_params() raised %r'
                                 % (self.module_id_name, err))

            try:
                schema.validate(values)
            except ValueError as err:
                raise ValueError('%s.migrate_params() gave bad output: %s'
                                 % (self.module_id_name, str(err)))

            return values
        else:
            return schema.coerce(values)

    @classmethod
    def for_module_version_sync(
        cls,
        module_version: Optional[ModuleVersion]
    ) -> 'LoadedModule':
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
            return DeletedModule()

        module_id_name = module_version.id_name
        version_sha1 = module_version.source_version_hash

        try:
            module = InternalModules[module_id_name]
            version_sha1 = 'internal'
        except KeyError:
            module = load_external_module(module_id_name, version_sha1,
                                          module_version.last_update_time)

        render_impl = getattr(module, 'render', _default_render)
        fetch_impl = getattr(module, 'fetch', _default_fetch)
        migrate_params_impl = getattr(module, 'migrate_params', None)

        return cls(module_id_name, version_sha1,
                   render_impl=render_impl, fetch_impl=fetch_impl,
                   migrate_params_impl=migrate_params_impl)


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
    if key == 'setup.py':
        return False
    if key.startswith('test_'):
        return False
    return key.endswith('.py')


def _load_external_module_uncached(module_id_name: str,
                                   version_sha1: str) -> ModuleType:
    """
    Load a Python Module given a name and version.
    """
    prefix = '%s/%s/' % (module_id_name, version_sha1)
    all_keys = minio.list_file_keys(minio.ExternalModulesBucket, prefix)
    python_code_key = next(k for k in all_keys
                           if _is_basename_python_code(k[len(prefix):]))

    with minio.temporarily_download(minio.ExternalModulesBucket,
                                    python_code_key) as tf:
        # Now we can load the code into memory.
        name = '%s.%s' % (module_id_name, version_sha1)
        logger.info(f'Loading {name} from {tf.name}')
        return module_loader.load_python_module(name, Path(tf.name))


def load_external_module(module_id_name: str, version_sha1: str,
                         last_update_time: datetime.datetime) -> ModuleType:
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
            module_version.id_name,
            module_version.source_version_hash
        )


def _internal_module_get_html_bytes(id_name: str) -> Optional[bytes]:
    try:
        with open(
            Path(__file__).parent.parent / 'modules' / f'{id_name}.html',
            'rb'
        ) as f:
            return f.read()
    except FileNotFoundError:
        return None


def _external_module_get_html_bytes(id_name: str,
                                    version: str) -> Optional[bytes]:
    prefix = '%s/%s/' % (id_name, version)
    all_keys = minio.list_file_keys(minio.ExternalModulesBucket, prefix)
    try:
        html_key = next(k for k in all_keys if k.endswith('.html'))
    except StopIteration:
        return None  # there is no HTML file

    with minio.open_for_read(minio.ExternalModulesBucket, html_key) as f:
        return f.read()
