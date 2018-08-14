from functools import lru_cache
import importlib
import importlib.util
import logging
import os
import sys
import traceback
from types import ModuleType
from typing import Any, Dict, Optional
from django.conf import settings
from pandas import DataFrame
from server.models import WfModule
from server.modules.types import ProcessResult
from server.modules.moduleimpl import ModuleImpl


logger = logging.getLogger(__name__)


# the base directory where all modules imported should be stored, i.e. the
# place where we go to lookup modules that aren't pre-loaded when the workbench
# starts up.
_DYNAMIC_MODULES_BASE_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    '..',
    'importedmodules'
)


class DynamicModule:
    """A module with `fetch` and `render` methods.
    """
    def __init__(self, module_id_name: str, version_sha1: str):
        self.module_id_name = module_id_name
        self.version_sha1 = version_sha1
        self.module = load_module(module_id_name, version_sha1)

    @property
    def has_render(self):
        """If false, render() returns its cached value (default empty).
        """
        return hasattr(self.module, 'fetch')

    def _default_render(self, wf_module, table) -> ProcessResult:
        """Render cached value, or pass-through input.
        """
        stored_table = wf_module.retrieve_fetched_table()
        fetch_error = wf_module.fetch_error
        if stored_table is not None or fetch_error:
            # Return cached value
            return ProcessResult(
                dataframe=stored_table,
                error=fetch_error
            )
        else:
            # Pass-through input
            return ProcessResult(dataframe=table)

    def _call_method(self, method_name: str, *args, **kwargs) -> ProcessResult:
        """
        Call module.method_name(*params, **kwargs) and coerce result.

        Exceptions become error messages. This method cannot produce an
        exception.
        """
        method = getattr(self.module, method_name)
        try:
            out = method(*args, **kwargs)
        except Exception as e:
            from server.importmodulefromgithub import original_module_lineno
            # Catch exceptions in the module render function, and return error
            # message + line number to user
            exc_name = type(e).__name__
            exc_type, exc_obj, exc_tb = sys.exc_info()
            # [1] = where the exception ocurred, not the render() just above
            tb = traceback.extract_tb(exc_tb)[1]
            fname = os.path.split(tb[0])[1]
            lineno = original_module_lineno(tb[1])
            error = f'{exc_name}: {str(e)} at line {lineno} of {fname}'
            return ProcessResult(error=error)

        out = ProcessResult.coerce(out)
        out.truncate_in_place_if_too_big()
        out.sanitize_in_place()
        return out

    def render(self, wf_module: WfModule,
               table: Optional[DataFrame]) -> ProcessResult:
        """Process `table` with module `render` method, for a ProcessResult.

        If the `render` method raises an exception, this method will return an
        error string. It is always an error for a module to raise an exception.
        """
        if table is None:
            return None  # TODO disallow?

        if not hasattr(self.module, 'render'):
            return self._default_render(wf_module, table)

        params = wf_module.create_parameter_dict(table)

        return self._call_method('render', table, params)

    def call_fetch(self, params: Dict[str, Any]) -> ProcessResult:
        """
        Process `params` with module `fetch` method, to build a ProcessResult.

        If the `fetch` method raises an exception, this method will return an
        error string. It is always an error for a module to raise an exception.
        """
        return self._call_method('fetch', params)

    def fetch(self, wf_module: WfModule) -> None:
        """Run `call_fetch(wf_module)` and write to `wf_module`.

        `wf_module` will be set to `busy` until the fetch completes. After,
        it will be either `ready` or `error`.
        """
        # FIXME database writes probably belong in dispatch.py. Right now,
        # here, half is dispatch stuff and half is database stuff.
        if not hasattr(self.module, 'fetch'):
            return

        params = wf_module.create_parameter_dict(None)

        wf_module.set_busy(notify=False)

        result = self.call_fetch(params)
        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        ModuleImpl.commit_result(wf_module, result)


def load_module(module_id_name: str, version_sha1: str) -> ModuleType:
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
        _DYNAMIC_MODULES_BASE_DIRECTORY,
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
    load_module = lru_cache(maxsize=None)(load_module)


def wf_module_to_dynamic_module(wf_module: WfModule) -> DynamicModule:
    """Return module referenced by `wf_module`.

    We assume:

    * the ModuleVersion and Module are in the database (foreign keys prove it)
    * the files exist on disk
    * the files were validated before being written to the database
    * the files haven't changed
    * the files' dependencies are in our PYTHONPATH
    * the files' dependencies haven't changed (i.e., its imports)

    ... in short: this function shouldn't raise an error.
    """
    module_id_name = wf_module.module_version.module.id_name
    version_sha1 = wf_module.module_version.source_version_hash

    return DynamicModule(module_id_name, version_sha1)


# -- Main entrypoints --

def get_module_render_fn(wf_module):
    dynamic_module = wf_module_to_dynamic_module(wf_module)
    return dynamic_module.render  # bound method


def get_module_html_path(wf_module):
    module_id_name = wf_module.module_version.module.id_name
    version_sha1 = wf_module.module_version.source_version_hash

    path_to_file = os.path.join(_DYNAMIC_MODULES_BASE_DIRECTORY,
                                module_id_name, version_sha1)

    for f in os.listdir(path_to_file):
        if f.endswith(".html"):
            return os.path.join(path_to_file, f)

    return ''
