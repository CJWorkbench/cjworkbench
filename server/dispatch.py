# Module dispatch table and implementations
import pandas as pd
from typing import Optional
from server.models import WfModule
from server.modules.types import ProcessResult
from .dynamicdispatch import get_module_render_fn, \
        get_module_html_path, wf_module_to_dynamic_module
from .modules.counybydate import CountByDate
from .modules.formula import Formula
from .modules.loadurl import LoadURL
from .modules.moduleimpl import ModuleImpl
from .modules.pastecsv import PasteCSV
from .modules.pythoncode import PythonCode
from .modules.selectcolumns import SelectColumns
from .modules.twitter import Twitter
from .modules.uploadfile import UploadFile
from .modules.googlesheets import GoogleSheets
from .modules.editcells import EditCells
from .modules.refine import Refine
from .modules.urlscraper import URLScraper
from .modules.scrapetable import ScrapeTable
from .modules.sortfromtable import SortFromTable
from .modules.reorder import ReorderFromTable
from .modules.rename import RenameFromTable
from .modules.duplicatecolumnfromtable import DuplicateColumnFromTable

# ---- Test Support ----


class NOP(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        return table


class DoubleMColumn(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        table['M'] *= 2
        return table


# ---- Interal modules Dispatch Table ----

module_dispatch_tbl = {
    'loadurl':          LoadURL,
    'pastecsv':         PasteCSV,
    'formula':          Formula,
    'selectcolumns':    SelectColumns,
    'pythoncode':       PythonCode,
    'twitter':          Twitter,
    'countbydate':      CountByDate,
    'uploadfile':       UploadFile,
    'googlesheets':     GoogleSheets,
    'editcells':        EditCells,
    'refine':           Refine,
    'urlscraper':       URLScraper,
    'scrapetable':      ScrapeTable,
    'sort-from-table':  SortFromTable,
    'reorder-columns':  ReorderFromTable,
    'rename-columns':   RenameFromTable,
    'duplicate-column-from-table': DuplicateColumnFromTable,

    # For testing
    'NOP':          NOP,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----


# TODO make all modules look like the ones in dynamicdispatch.py, then nix
# this method.
def _module_dispatch_render_static(dispatch, wf_module, table):
    result = dispatch.render(wf_module, table)
    result = ProcessResult.coerce(result)
    result.truncate_in_place_if_too_big()
    result.sanitize_in_place()
    return result


# Main render entrypoint.
def module_dispatch_render(wf_module: WfModule,
                           table: pd.DataFrame) -> ProcessResult:
    """Sets wf_module error/status and returns its ProcessResult.
    """
    if wf_module.module_version is None:
        return ProcessResult(pd.DataFrame())  # happens if module deleted

    render_fn = None

    dispatch = wf_module.module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        result = _module_dispatch_render_static(
            module_dispatch_tbl[dispatch],
            wf_module,
            table
        )
    else:
        render_fn = get_module_render_fn(wf_module)
        result = render_fn(wf_module, table)

    if result.error:
        wf_module.set_error(result.error, notify=True)
    else:
        if wf_module.status != WfModule.READY:
            # set notify=True to fix #157160567 if bad input is fixed, then
            # user can click module to refresh it, which notifies, which
            # clears error message in UI.
            #
            # Unresolved ickiness: if we change a parameter to fix an error, we
            # get two refreshes (the other is from ChangeParameterCommand)
            wf_module.set_ready(notify=True)

    return result


def module_dispatch_event(wf_module, **kwargs):
    dispatch = wf_module.module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        # Clear errors on every new event. (The other place they are cleared is
        # on parameter change)
        wf_module.set_ready(notify=False)
        return module_dispatch_tbl[dispatch].event(wf_module, **kwargs)
    else:
        dynamic_module = wf_module_to_dynamic_module(wf_module)
        dynamic_module.fetch(wf_module)


def module_get_html_bytes(wf_module) -> Optional[bytes]:
    dispatch = wf_module.module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        # No internal modules have HTML outputs
        return None

    html_file_path = get_module_html_path(wf_module)
    with open(html_file_path, 'rb') as f:
        return f.read()
