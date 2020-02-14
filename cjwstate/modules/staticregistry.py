"""
Built-in Workbench modules.

These modules have the same API as external modules. We bundle each with
Workbench for at least one of these reasons:

    * We feel every Workbench user needs the module.
    * The module uses Workbench-internal APIs.
    * The module uses experimental Workbench APIs, which may change. (We keep
      it internal to pin the module code to the API code.)
    * Legacy reasons.

Defining modules
================

Modules are declared by a ".json" spec file, which must be named after the
module id. The ".py" file must have the same name; a ".html" file is
allowed, too.

Each module may define one or both (preferably one) of the following functions:

    def render(table: pd.DataFrame, params: Params, **kwargs):
        # kwargs is optional and may include:
        # - input_columns: Dict of .name/.type values, keyed by table.columns
        return table

    async def fetch(  # async is optional and preferred
        params: Params,
        **kwargs
    ) -> ProcessResult:
        # kwargs is optional and may include:
        # - get_input_dataframe: Callable[[], Awaitable[pd.DataFrame]]
        # - get_stored_dataframe: Callable[[], Awaitable[pd.DataFrame]]
    ) -> ProcessResult:

Looking up modules
==================

This ``registry.py`` imports all the modules automatically, finding them by
their ``.json`` spec files.

>>> import cjwstate.modules
>>> from cjwstate.modules import staticregistry
>>> cjwstate.modules.init_module_system()
>>> staticregistry.Lookup['pythoncode']  # dynamic lookup by id
"""
import logging
from pathlib import Path
from typing import Dict
import zipfile
import staticmodules
from .types import ModuleZipfile


logger = logging.getLogger(__name__)


Lookup: Dict[str, ModuleZipfile] = {}


MODULE_TEMPDIR = Path("/var/tmp/cjwkernel-modules")


def _setup(kernel):
    MODULE_TEMPDIR.mkdir(exist_ok=True)

    spec_paths = list(Path(staticmodules.__file__).parent.glob("*.yaml"))
    for spec_path in spec_paths:
        logger.info("Importing %s...", spec_path)
        module_id = spec_path.stem

        # We leak these tempfiles ... but there's a fixed number of them and
        # Workbench already runs on docker so the tempfiles won't pile up
        # anywhere. TODO nix static modules, nixing this problem.
        zip_path = MODULE_TEMPDIR / ("%s.internal.zip" % spec_path.stem)
        with zipfile.ZipFile(zip_path, mode="w") as zf:
            zf.write(spec_path, spec_path.name)

            py_path = spec_path.with_suffix(".py")
            zf.write(py_path, py_path.name)

            html_path = spec_path.with_suffix(".html")
            if html_path.exists():
                zf.write(html_path, html_path.name)

        module_zipfile = ModuleZipfile(zip_path)
        spec = module_zipfile.get_spec()  # raise ValueError
        assert (
            spec.parameters_version is not None
        ), "Internal modules require a 'parameters_version'"

        # raise SyntaxError
        compiled_module = module_zipfile.compile_code_without_executing()
        kernel.validate(compiled_module)

        Lookup[module_id] = module_zipfile
