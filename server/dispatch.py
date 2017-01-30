# Module dispatch table and implementations
from server.models import Module, WfModule
import pandas as pd

# ---- Module implementations ---

# Base class for all modules. Really just a reminder of function signaturs
class ModuleImpl:
    @staticmethod
    def render(wfmodule, table):
        return table

    @staticmethod
    def event(parameter, e):
        pass


class LoadCSV(ModuleImpl):

    # input table ignored
    @staticmethod
    def render(wfmodule, table):
        url = wfmodule.get_param_string("URL")
        table = pd.DataFrame(columns=['url'])
        table.loc[0] = url
        return table

    @staticmethod
    def event(parameter, e):
        print('LoadCSV got event %s' % str(e))


class Formula(ModuleImpl):
    pass

class RawCode(ModuleImpl):
    pass

class Chart(ModuleImpl):
    pass

class TestDataRows(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        table = pd.DataFrame(columns=['N', 'N squared'])
        rows = wfmodule.get_param_number('Rows')
        for i in range(int(rows)):
            table.loc[i] = [i+1, (i+1)*(i+1)]
        return table

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


module_dispatch_tbl = {
    'loadcsv':      LoadCSV,
    'formula':      Formula,
    'rawcode':      RawCode,
    'simplechart':  Chart,
    'testdataN':    TestDataRows,

    # For testing
    'NOP':          NOP,
    'testdata':     TestData,
    'double_M_col': DoubleMColumn
}

# ---- Dispatch Entrypoints ----

def module_dispatch_render(wf_module, table):
    dispatch = wf_module.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        raise ValueError('Unknown render dispatch %s for module %s' % (dispatch, wf_module.module.name))

    return module_dispatch_tbl[dispatch].render(wf_module,table)


def module_dispatch_event(parameter, event):
    dispatch = parameter.wf_module.module.dispatch
    if dispatch not in module_dispatch_tbl.keys():
        raise ValueError('Unknown event dispatch %s for parameter %s' % (dispatch, parameter.name))

    return module_dispatch_tbl[dispatch].event(parameter, event)
