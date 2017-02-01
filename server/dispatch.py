# Module dispatch table and implementations
from server.models import Module, WfModule
import pandas as pd
import requests
import io
import csv
from server.versions import bump_workflow_version

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
        table = wfmodule.retrieve_text('csv')
        if table != None:
            table = pd.read_csv(io.StringIO(table))
        return table

    # Load a CSV from file when fetch pressed
    @staticmethod
    def event(parameter, e):
        wfm = parameter.wf_module

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()
        csvres = requests.get(wfm.get_param_string("URL"))

        if csvres.status_code != requests.codes.ok:
            wfm.set_error('Error %s fetching url' % str(csvres.status_code))
            return

        table = pd.read_csv(io.StringIO(csvres.text))
        wfm.store_text('csv', table.to_csv(index=False))      # index=False to prevent pandas from adding an index col

        # we are done. notify of changes to the workflow, reset status light
        bump_workflow_version(wfm.workflow)
        wfm.set_ready()




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
