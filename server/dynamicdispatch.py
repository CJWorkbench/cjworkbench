from .models import WfModule

import importlib, inspect, os
import importlib.util
from pandas import DataFrame
from types import ModuleType
from typing import Any, Optional, Dict, Tuple
from functools import lru_cache


#the base directory where all modules imported should be stored, i.e. the place where we go to lookup
#modules that aren't pre-loaded when the workbench starts up.
_DYNAMIC_MODULES_BASE_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    '..',
    'importedmodules'
)


class DynamicModuleError(Exception):
    pass



class DynamicModule:
    """A module with `fetch` and `render` methods.
    """
    def __init__(self, module_id_name: str, version_sha1: str):
        self.module_id_name = module_id_name
        self.version_sha1 = version_sha1
        self.module = load_module(module_id_name, version_sha1)


    def render(self, table: Optional[DataFrame],
               params: Dict[str, Any]) -> Tuple[str, DataFrame]:
        """Process `table` with module `render` method, to build a new
        DataFrame.

        If the `render` method raises an exception, this method will return an
        error string. It is always an error for a module to raise an exception.

        The `render` method's return value will be coerced into a
        ``(error_string, output_table)`` format. At least one will be non-None.
        """
        if table is None: return None

        # TODO handle exceptions, coerce return value
        return self.module.render(table, params)


@lru_cache(maxsize=None)
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

    # for now, we are working on the assumption that there's a single Python file per importable module, so
    # we can just find the single file that should be in this directory, and boom, job done.
    for f in os.listdir(path_to_code):
        if f == 'setup.py': continue

        if f.endswith(".py"):
            python_file = os.path.join(path_to_code, f)
            break
    else:
        raise ValueError(f'Expected .py file in {path_to_code}')

    #Now we can load the code into memory.
    spec = importlib.util.spec_from_file_location(
        f'{module_id_name}.{version_sha1}',
        python_file
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    return dynamic_module.render # bound method


def get_module_html_path(wf_module):
    module_version = ModuleVersion.objects.filter(module=wf_module.module_version.module,
                                source_version_hash=wf_module.module_version.source_version_hash)

    path_to_file = os.path.join(_DYNAMIC_MODULES_BASE_DIRECTORY, wf_module.module_version.module.id_name,
                                    wf_module.module_version.source_version_hash)

    for f in os.listdir(path_to_file):
        if f.endswith(".html"):
            return os.path.join(path_to_file, f)

    return ''
