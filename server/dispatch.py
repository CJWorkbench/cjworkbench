import asyncio
from inspect import iscoroutinefunction
import logging
import time
import traceback
from typing import Optional
import pandas as pd
from server import versions
from server.models import ModuleVersion, Params
from server.modules.types import ProcessResult
from .dynamicdispatch import get_module_render_fn, \
        get_module_html_path, module_version_to_dynamic_module
from .modules.countbydate import CountByDate
from .modules.formula import Formula
from .modules.loadurl import LoadURL
from .modules.moduleimpl import ModuleImpl
from .modules.pastecsv import PasteCSV
import server.modules.pythoncode
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
from .modules.duplicatecolumn import DuplicateColumn
from .modules.joinurl import JoinURL
from .modules.concaturl import ConcatURL


# ---- Test Support ----
class NOP(ModuleImpl):
    @staticmethod
    def render(params, table, **kwargs):
        return table


class DoubleMColumn(ModuleImpl):
    @staticmethod
    def render(params, table, **kwargs):
        table['M'] *= 2
        return table


logger = logging.getLogger(__name__)


# ---- Interal modules Dispatch Table ----
module_dispatch_tbl = {
    'loadurl':          LoadURL,
    'pastecsv':         PasteCSV,
    'formula':          Formula,
    'selectcolumns':    SelectColumns,
    'pythoncode':       server.modules.pythoncode,
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
    'duplicate-column': DuplicateColumn,
    'joinurl':          JoinURL,
    'concaturl':        ConcatURL,

    # For testing
    'NOP':          NOP,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----


# TODO make all modules look like the ones in dynamicdispatch.py, then nix
# this method.
def _module_dispatch_render_static(dispatch, params, table, fetch_result):
    try:
        result = dispatch.render(params, table, fetch_result=fetch_result)
    except Exception as err:
        traceback.print_exc()
        result = ProcessResult(error=f'Internal error: {err}')

    result = ProcessResult.coerce(result)
    result.truncate_in_place_if_too_big()
    result.sanitize_in_place()
    return result


# Main render entrypoint.
def module_dispatch_render(module_version: ModuleVersion,
                           params: Params,
                           table: pd.DataFrame,
                           fetch_result: Optional[ProcessResult]
                           ) -> ProcessResult:
    """
    Calls a module's `render()` and returns a sane ProcessResult.
    """
    if not module_version:  # module was deleted
        return ProcessResult(
            error='This module code has been uninstalled. Please delete it.'
        )

    render_fn = None

    time1 = time.time()

    dispatch = module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        result = _module_dispatch_render_static(
            module_dispatch_tbl[dispatch],
            params,
            table,
            fetch_result
        )
    else:
        render_fn = get_module_render_fn(module_version)
        result = render_fn(params, table, fetch_result)

    time2 = time.time()
    logger.info('%s rendered (%drows,%dcols)=>(%drows,%dcols) in %dms',
                str(module_version), table.shape[0], table.shape[1],
                result.dataframe.shape[0], result.dataframe.shape[1],
                int((time2 - time1) * 1000))

    return result


async def _module_dispatch_fetch_static(module_version, wf_module):
    """
    Run module `fetch()` method.

    `fetch()` returns `None` if it wants a no-op (e.g., input values are not
    set); otherwise it returns a ProcessResult.
    """
    dispatch = module_version.module.dispatch
    module_dispatch = module_dispatch_tbl[dispatch]
    if not hasattr(module_dispatch, 'fetch'):
        return None

    time1 = time.time()

    fetch = module_dispatch.fetch
    if iscoroutinefunction(fetch):
        result = await fetch(wf_module)
    else:
        # TODO nix all synchronous fetches and nix this code
        loop = asyncio.get_event_loop()
        if loop.is_running():
            result = loop.run_in_executor(None, fetch, wf_module)
        else:
            # No event loop
            result = fetch(wf_module)
    time2 = time.time()

    shape = result.dataframe.shape if result is not None else (-1, -1)
    logger.info('%s fetched =>(%drows,%dcols) in %dms',
                str(module_version), shape[0], shape[1],
                int((time2 - time1) * 1000))

    return result


async def module_dispatch_fetch(wf_module) -> None:
    module_version = wf_module.module_version
    dispatch = module_version.module.dispatch

    if dispatch in module_dispatch_tbl:
        result = await _module_dispatch_fetch_static(module_version, wf_module)
    else:
        dynamic_module = module_version_to_dynamic_module(module_version)
        result = await dynamic_module.fetch(wf_module)

    await versions.save_result_if_changed(wf_module, result)


def module_get_html_bytes(module_version) -> Optional[bytes]:
    dispatch = module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        try:
            # Store _path_, not _bytes_, in the module. Django's autoreload
            # won't notice when the HTML changes in dev mode, so it's hard to
            # develop if the module stores the bytes themselves.
            html_path = module_dispatch_tbl[dispatch].html_path
            with open(html_path, 'rb') as f:
                return f.read()
        except AttributeError:
            return None

    html_file_path = get_module_html_path(module_version)
    with open(html_file_path, 'rb') as f:
        return f.read()
