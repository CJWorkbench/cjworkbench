# Module dispatch table and implementations
import pandas as pd
from django.conf import settings
from server.models import WfModule
from server.models.ParameterSpec import ParameterSpec
from server.models.ParameterVal import ParameterVal
from .dynamicdispatch import get_module_render_fn, get_module_html_path, wf_module_to_dynamic_module
from .sanitizedataframe import sanitize_dataframe, truncate_table_if_too_big
import os, inspect
from django.utils.translation import gettext as _

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

    # For testing
    'NOP':          NOP,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----

# Main render entrypoint.
def module_dispatch_render(wf_module, table):
    if wf_module.module_version is None:
        return pd.DataFrame()  # happens if module deleted

    render_fn = None

    dispatch = wf_module.module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        render_fn = module_dispatch_tbl[dispatch].render
    else:
        render_fn = get_module_render_fn(wf_module)

    tableout = render_fn(wf_module, table)
    error = None

    if isinstance(tableout, str):
        # a string is an error message, and there is no table
        (tableout, error) = (table, tableout) # weird? output = input

    if isinstance(tableout, tuple) and len(tableout) == 2:
        # a tuple is what we expect: (table, error)
        (tableout, error) = tableout

    if (tableout is not None) and (not isinstance(tableout, pd.DataFrame)):
        # if it's not a string or a tuple it needs to be a table
        error = _('Module did not return a table or an error message')
        tableout = None

    if tableout is None:
        tableout = pd.DataFrame()

    # Restrict to row limit. We set an error, but still return the output table
    nrows = len(tableout)
    if truncate_table_if_too_big(tableout):
        error = _('Output has %d rows, truncated to %d' % (nrows, settings.MAX_ROWS_PER_TABLE))

    if error:
        wf_module.set_error(error, notify=True)
    else:
        if wf_module.status != WfModule.READY:
            # set notify=True to fix #157160567 if bad input is fixed, then
            # user can click module to refresh it, which notifies, which
            # clears error message in UI.
            #
            # Unresolved ickiness: if we change a parameter to fix an error, we
            # get two refreshes (the other is from ChangeParameterCommand)
            wf_module.set_ready(notify=True)

    tableout = sanitize_dataframe(tableout)  # Ensure correct column types etc.
    return tableout


def module_dispatch_event(wf_module, **kwargs):
    dispatch = wf_module.module_version.module.dispatch
    if dispatch in module_dispatch_tbl:
        # Clear errors on every new event. (The other place they are cleared is on parameter change)
        wf_module.set_ready(notify=False)
        return module_dispatch_tbl[dispatch].event(wf_module, **kwargs)
    else:
        dynamic_module = wf_module_to_dynamic_module(wf_module)
        dynamic_module.fetch(wf_module)


def module_dispatch_output(wf_module, table, **kwargs):
    dispatch = wf_module.module_version.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        html_file_path = get_module_html_path(wf_module)
    else:
        module_path = os.path.dirname(inspect.getfile(module_dispatch_tbl[dispatch]))
        for f in os.listdir(module_path):
            if f.endswith(".html"):
                html_file_path = os.path.join(module_path, f)
                break

    tableout = module_dispatch_render(wf_module, table)
    params = wf_module.create_parameter_dict(table)
    # got some error handling in here if, for some reason, someone tries to call
    # output on this and it doesn't have any defined html output
    html_file = open(html_file_path, 'r+', encoding="utf-8")
    html_str = html_file.read()

    return (html_str, tableout, params)
