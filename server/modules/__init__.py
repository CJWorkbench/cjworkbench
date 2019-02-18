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
module id_name. The ".py" file must have the same name; a ".html" file is
allowed, too.

Each module may define one or both (preferably one) of the following functions:

    def render(table: pd.DataFrame, params: Params, **kwargs) -> ProcessResult:
        # kwargs is optional and may include:
        # - input_columns: Dict of .name/.type values, keyed by table.columns
        return ProcessResult(table)

    async def fetch(  # async is optional and preferred
        params: Params,
        **kwargs
    ) -> ProcessResult:
        # kwargs is optional and may include:
        # - workflow_id: int
        # - get_input_dataframe: Callable[[], Awaitable[pd.DataFrame]]
        # - get_stored_dataframe: Callable[[], Awaitable[pd.DataFrame]]
        # - get_workflow_owner: Callable[[], Awaitable[User]]
    ) -> ProcessResult:

Looking up modules
==================

This ``__init__.py`` imports all the modules automatically, finding them by
their ``.json`` spec files.

>>> from server import modules
>>> modules.pythoncode  # direct access
>>> modules.Lookup['pythoncode']  # dynamic lookup by id_name
"""
import importlib
import pathlib
from server.models.module_loader import ModuleFiles, ModuleSpec


Lookup = {}
Specs = {}

SpecPaths = (
    list(pathlib.Path(__file__).parent.glob('*.json'))
    + list(pathlib.Path(__file__).parent.glob('*.yaml'))
)
for spec_path in SpecPaths:
    spec = ModuleSpec.load_from_path(spec_path)
    id_name = spec_path.stem
    module = importlib.import_module('.' + id_name, __package__)
    Lookup[id_name] = module
    Specs[id_name] = spec
