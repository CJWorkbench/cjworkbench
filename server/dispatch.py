# Module dispatch table and implementations
import pandas as pd
from django.conf import settings

from .modules.chart import Chart
from .modules.countvalues import CountValues
from .modules.counybydate import CountByDate
from .modules.formula import Formula
from .modules.loadurl import LoadURL
from .modules.moduleimpl import ModuleImpl
from .modules.pastecsv import PasteCSV
from .modules.pythoncode import PythonCode
from .modules.selectcolumns import SelectColumns
from .modules.textsearch import TextSearch
from .modules.twitter import Twitter

from .dynamicdispatch import DynamicDispatch
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
    'countvalues':  CountValues,
    'countbydate':  CountByDate,

    # For testing
    'NOP':          NOP,
    'testdata':     TestData,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----

dynamic_dispatch = DynamicDispatch()

#the wf_module should have both attributes: the module and the version.
def load_dynamically(wf_module, table, dispatch):
    #check if dispatch is loadable dynamically; if so, load it.
    # print("Loading {} manually".format(dispatch))
    return dynamic_dispatch.load_module(wf_module=wf_module, table=table, dispatch=dispatch)

def module_dispatch_render(wf_module, table):
    dispatch = wf_module.module_version.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        loadable = load_dynamically(wf_module=wf_module, table=table, dispatch=dispatch)
        if not loadable:
            raise ValueError('Unknown render dispatch %s for module %s' % (dispatch, wf_module.module.name))
        else:
            return loadable.render(wf_module, table)

    return module_dispatch_tbl[dispatch].render(wf_module,table)


def module_dispatch_event(wf_module, parameter, event):
    dispatch = wf_module.module_version.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        raise ValueError("Unknown dispatch id '%s' while handling event for parameter '%s'" % (dispatch, parameter.parameter_spec.name))

    return module_dispatch_tbl[dispatch].event(wf_module, parameter, event)
