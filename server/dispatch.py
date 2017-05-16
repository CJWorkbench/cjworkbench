# Module dispatch table and implementations
#from server.models import Module, WfModule
from django.conf import settings
import pandas as pd
from pandas.parser import CParserError
import re
import io
import os
import csv
import json
from server.versions import bump_workflow_version
from .modules.moduleimpl import ModuleImpl
from .modules.twitter import Twitter
from .modules.loadurl import LoadURL
from .modules.pastecsv import PasteCSV
from .modules.selectcolumns import SelectColumns
from .modules.textsearch import TextSearch
from .modules.formula import Formula
from .modules.pythoncode import PythonCode
from .modules.chart import Chart

# ---- Test Support ----

# NOP -- do nothing

class NOP(ModuleImpl):
    pass


# Generate test data

test_data_table = pd.DataFrame( {   'Class' : ['math', 'english', 'history'],
                                    'M'     : [ '10', '5', '11' ],
                                    'F'     : [ '12', '7', '13'] } )
class TestData(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        return test_data_table

class DoubleMColumn(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        return pd.DataFrame(table['Class'], table['M']*2, table['F'])


# ---- Main Dispatch Table ----

module_dispatch_tbl = {
    'loadurl':      LoadURL,
    'pastecsv':     PasteCSV,
    'formula':      Formula,
    'selectcolumns':SelectColumns,
    'pythoncode':   PythonCode,
    'simplechart':  Chart,
    'twitter':      Twitter,
    'textsearch':   TextSearch,

    # For testing
    'NOP':          NOP,
    'testdata':     TestData,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----

def module_dispatch_render(wf_module, table):
    dispatch = wf_module.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        if not settings.DEBUG:
            raise ValueError('Unknown render dispatch %s for module %s' % (dispatch, wf_module.module.name))
        else:
            return table  # in debug it just becomes a NOP

    return module_dispatch_tbl[dispatch].render(wf_module,table)


def module_dispatch_event(parameter, event):
    dispatch = parameter.wf_module.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        raise ValueError('Unknown event dispatch %s for parameter %s' % (dispatch, parameter.name))

    return module_dispatch_tbl[dispatch].event(parameter, event)
