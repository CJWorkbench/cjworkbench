# Module dispatch table and implementations
from server.models import Module, WfModule
import pandas as pd
import numpy as np
from pandas.parser import CParserError
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

# ---- LoadCSV ----

class LoadCSV(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        tablestr = wf_module.retrieve_text('csv')
        if (tablestr != None) and (len(tablestr)>0):
            return pd.read_csv(io.StringIO(tablestr))
        else:
            return None

    # Load a CSV from file when fetch pressed
    @staticmethod
    def event(parameter, e):
        wfm = parameter.wf_module

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()
        url = wfm.get_param_string('url')
        res = requests.get(url)

        if res.status_code != requests.codes.ok:
            wfm.set_error('Error %s fetching url' % str(csvres.status_code))
            return

        content_type = res.headers.get('content-type')
        print('content type of %s: %s' % (url, content_type))

        if content_type == 'text/csv':
            try:
                table = pd.read_csv(io.StringIO(res.text))
            except CParserError as e:
                wf_module.set_error(str(e))

        elif content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            try:
                table = pd.read_excel(io.BytesIO(res.content))
            except CParserError as e:
                wf_module.set_error(str(e))

        elif content_type == 'aaplication/json':
            try:
                table_json = res.json()
                path = wfm.get_param_string('json_path')
                for p in path.split('.'):
                    table_json = table_json[p]
                table = pd.DataFrame(table_json)

            except KeyError as e:
                wf_module.set_error('JSON data has no field %s' % p)

            except CParserError as e:
                wf_module.set_error(str(e))

        else:
            wfm.set_error('Error fetching %s: unknown content type %s' % (url,content_type))

        if wfm.status == WfModule.ERROR:
            return None

        # we are done. save fetched data, notify of changes to the workflow, reset status
        wfm.store_text('csv', table.to_csv(index=False))      # index=False to prevent pandas from adding an index col
        wfm.set_ready(notify=False)
        bump_workflow_version(wfm.workflow)


# ---- PasteCSV ----
# Lets the user paste in text which it interprets as a exce
class PasteCSV(ModuleImpl):
    def render(wf_module, table):
        tablestr = wf_module.get_param_text("csv")

        if (len(tablestr)==0):
            wf_module.set_error('Please enter a CSV')
            return None
        try:
            table = pd.read_csv(io.StringIO(tablestr))
        except CParserError as e:
            wf_module.set_error(str(e))
            return None

        wf_module.set_ready(notify=False)
        return table


# ---- Unimplemented ----

class Formula(ModuleImpl):
    def render(wf_module, table):
        formula = wf_module.get_param_string('formula')
        colnames = list(table.columns)
        newcol = pd.Series(np.zeros(len(table)))

        # hmm, this is going to need more work
        globals = {
            '__builtins__': {},      # disallow import etc. (though still not impossible!)
            'str' : str
        }

        # Catch errors with the formula and display to user
        try:
            code = compile(formula, '<string>', 'eval')

            # Much experimentation went into the form of this loop for good performance.
            # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
            for i,row in enumerate(table.values):
                newcol[i] = eval(code  , globals, dict(zip(colnames, row)))
        except Exception as e:
            wf_module.set_error(str(e))
            return None

        # if no output column supplied, use result0, result1, etc.
        out_column = wf_module.get_param_string('out_column')
        if out_column == '':
            if 'result' not in colnames:
                out_column='result'
            else:
                n=0
                while 'result' + str(n) in colnames:
                    n+=1
                out_column = 'result' + str(n)
        table[out_column] = newcol

        wf_module.set_ready(notify=False)
        return table

class Scale(ModuleImpl):
    def render(wf_module, table):
        column = wf_module.get_param_string('column')

        print(table.columns)
        if not column in table.columns:
            wf_module.set_error('Column not found')
            return None

        scale = wf_module.get_param_number('scale')
        table.loc[:, column] *= scale
        wf_module.set_ready(notify=False)
        return table

class RawCode(ModuleImpl):
    pass

class Chart(ModuleImpl):
    pass

class TestDataRows(ModuleImpl):
    @staticmethod
    def render(wfmodule, table):
        table = pd.DataFrame(columns=['N', 'N squared'])
        rows = wfmodule.get_param_number('rows')
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
    'pastecsv':     PasteCSV,
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
