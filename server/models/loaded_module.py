import asyncio
from collections import namedtuple
from functools import lru_cache, partial
import importlib
import importlib.util
import inspect
import logging
import os
import sys
import time
import traceback
from types import ModuleType
from typing import Awaitable, Callable, Optional
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import User
import pandas as pd
from .ModuleVersion import ModuleVersion
from .Params import Params
from ..modules.types import ProcessResult
from ..modules.countbydate import CountByDate
from ..modules.formula import Formula
from ..modules.loadurl import LoadURL
from ..modules.pastecsv import PasteCSV
import server.modules.pythoncode
from ..modules.selectcolumns import SelectColumns
from ..modules.twitter import Twitter
from ..modules.uploadfile import UploadFile
from ..modules.googlesheets import GoogleSheets
from ..modules.editcells import EditCells
from ..modules.refine import Refine
from ..modules.urlscraper import URLScraper
from ..modules.scrapetable import ScrapeTable
from ..modules.sortfromtable import SortFromTable
from ..modules.reorder import ReorderFromTable
from ..modules.rename import RenameFromTable
from ..modules.duplicatecolumn import DuplicateColumn
from ..modules.joinurl import JoinURL
from ..modules.concaturl import ConcatURL


logger = logging.getLogger(__name__)


def _double_M_col(params, table, **kwargs):
    table = table.copy()
    table['M'] *= 2
    return table


MockModule = namedtuple('MockModule', ['render'])


StaticModules = {
    'loadurl': LoadURL,
    'pastecsv': PasteCSV,
    'formula': Formula,
    'selectcolumns': SelectColumns,
    'pythoncode': server.modules.pythoncode,
    'twitter': Twitter,
    'countbydate': CountByDate,
    'uploadfile': UploadFile,
    'googlesheets': GoogleSheets,
    'editcells': EditCells,
    'refine': Refine,
    'urlscraper': URLScraper,
    'scrapetable': ScrapeTable,
    'sort-from-table': SortFromTable,
    'reorder-columns': ReorderFromTable,
    'rename-columns': RenameFromTable,
    'duplicate-column': DuplicateColumn,
    'joinurl': JoinURL,
    'concaturl': ConcatURL,

    # For testing. FIXME nix these
    'NOP': MockModule(lambda params, table, **kwargs: table),
    'double_M_col': MockModule(_double_M_col),
}


def _default_render(param1, param2,
                    *, fetch_result, **kwargs) -> ProcessResult:
    """Render fetch_result or pass-through input."""
    if fetch_result is not None:
        return fetch_result
    else:
        # Pass-through input.
        #
        # Internal and external modules have opposite calling conventions: one
        # takes (params, table) and the other takes (table, params). Return
        # whichever input is a pd.DataFrame.
        if isinstance(param1, pd.DataFrame):
            return ProcessResult(param1)
        else:
            return ProcessResult(param2)


async def _default_fetch(params, **kwargs) -> Optional[ProcessResult]:
    """No-op fetch."""
    return None


class LoadedModule:
    """A module with `fetch` and `render` methods.
    """
    def __init__(self, module_id_name: str, version_sha1: str,
                 is_external: bool=True,
                 render_impl: Optional[Callable]=_default_render,
                 fetch_impl: Optional[Callable]=_default_fetch):
        self.module_id_name = module_id_name
        self.version_sha1 = version_sha1
        self.is_external = is_external
        self.name = f'{module_id_name}:{version_sha1}'
        self.render_impl = render_impl
        self.fetch_impl = fetch_impl

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

        if self.is_external:
            from server.importmodulefromgithub import original_module_lineno
            lineno = original_module_lineno(lineno)

        error = f'{exc_name}: {str(err)} at line {lineno} of {fname}'
        return ProcessResult(error=error)

    def render(self, params: Params,
               table: Optional[pd.DataFrame],
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
        # Internal and external modules have different calling conventions
        if self.is_external:
            arg1, arg2 = (table, params.to_painful_dict(table))
        else:
            arg1, arg2 = (params, table)

        kwargs = {}
        spec = inspect.getfullargspec(self.render_impl)
        varkw = bool(spec.varkw)  # if True, function accepts **kwargs
        kwonlyargs = spec.kwonlyargs
        if varkw or 'fetch_result' in kwonlyargs:
            kwargs['fetch_result'] = fetch_result

        time1 = time.time()

        try:
            out = self.render_impl(arg1, arg2, **kwargs)
        except Exception as err:
            out = self._wrap_exception(err)

        out = ProcessResult.coerce(out)
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

        if self.is_external:
            # Pass input to params.to_painful_dict().
            input_dataframe_future = get_input_dataframe()

            input_dataframe = await input_dataframe_future
            if input_dataframe is None:
                input_dataframe = pd.DataFrame()
            params = params.to_painful_dict(input_dataframe)
            # If we're passing get_input_dataframe via kwargs, short-circuit it
            # because we already know the result.
            if 'get_input_dataframe' in kwargs:
                kwargs['get_input_dataframe'] = lambda: input_dataframe_future

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

    @classmethod
    def for_module_version_sync(
        cls,
        module_version: ModuleVersion
    ) -> 'LoadedModule':
        """
        Return module referenced by `module_version`.

        We assume:

        * the ModuleVersion and Module are in the database (foreign keys prove
          this)
        * external-module files exist on disk
        * external-module files were validated before being written to database
        * external-module files haven't changed
        * external-module files' dependencies are in PYTHONPATH
        * external-module files' dependencies haven't changed (i.e., imports)

        Invalid assumption? Fix the bug elsewhere.

        Do not call this from an async method, because you may leak a database
        connection. Use `for_module_version` instead.
        """
        module_id_name = module_version.module.id_name  # TODO DoesNotExist
        version_sha1 = module_version.source_version_hash

        try:
            module = StaticModules[module_id_name]
            version_sha1 = 'internal'
            is_external = False
        except KeyError:
            module = load_external_module(module_id_name, version_sha1)
            is_external = True

        render_impl = getattr(module, 'render', _default_render)
        fetch_impl = getattr(module, 'fetch', _default_fetch)

        return cls(module_id_name, version_sha1, is_external=is_external,
                   render_impl=render_impl, fetch_impl=fetch_impl)


def load_external_module(module_id_name: str, version_sha1: str) -> ModuleType:
    """Load a Python Module given a name and version.

    This is memoized.

    Assume:

    * the files exist on disk and are valid
    * the files never change
    * the files' dependencies are in our PYTHONPATH
    * the files' dependencies haven't changed (i.e., its imports)

    ... in short: this function shouldn't raise an error.
    """
    path_to_code = os.path.join(
        settings.IMPORTED_MODULES_ROOT,
        module_id_name,
        version_sha1
    )

    # for now, we are working on the assumption that there's a single Python
    # file per importable module, so we can just find the single file that
    # should be in this directory, and boom, job done.
    for f in os.listdir(path_to_code):
        if f == 'setup.py':
            continue

        if f.endswith(".py"):
            python_file = os.path.join(path_to_code, f)
            break
    else:
        raise ValueError(f'Expected .py file in {path_to_code}')

    # Now we can load the code into memory.
    logger.info(f'Loading {python_file}')
    spec = importlib.util.spec_from_file_location(
        f'{module_id_name}.{version_sha1}',
        python_file
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if settings.CACHE_MODULES:
    load_external_module = lru_cache(maxsize=None)(load_external_module)


def module_get_html_path(module_version: ModuleVersion) -> Optional[str]:
    module_id_name = module_version.module.id_name
    version_sha1 = module_version.source_version_hash

    if module_id_name in StaticModules:
        try:
            # Store _path_, not _bytes_, in the module. Django's autoreload
            # won't notice when the HTML changes in dev mode, so it's hard to
            # develop if the module stores the bytes themselves.
            return StaticModules[module_id_name].html_path
        except AttributeError:
            return None
    else:
        path_to_file = os.path.join(settings.IMPORTED_MODULES_ROOT,
                                    module_id_name, version_sha1)

        for f in os.listdir(path_to_file):
            if f.endswith('.html'):
                return os.path.join(path_to_file, f)

        return None


def module_get_html_bytes(module_version: ModuleVersion) -> Optional[bytes]:
    path = module_get_html_path(module_version)
    if path:
        with open(path, 'rb') as f:
            return f.read()
    else:
        return None
