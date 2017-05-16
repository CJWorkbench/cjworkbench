# Module dispatch table and implementations
#from server.models import Module, WfModule
from django.conf import settings
import pandas as pd
import numpy as np
from pandas.parser import CParserError
import re
import io
import os
import csv
import json
import math
from server.versions import bump_workflow_version
from .modules.moduleimpl import ModuleImpl
from .modules.twitter import Twitter
from .modules.loadurl import LoadURL

# ---- PasteCSV ----
# Lets the user paste in text which it interprets as a exce
class PasteCSV(ModuleImpl):

    def render(wf_module, table):
        tablestr = wf_module.get_param_string("csv")

        has_header_row = wf_module.get_param_checkbox("has_header_row")

        if has_header_row:
            header_row = 0
        else:
            header_row = None

        if (len(tablestr)==0):
            wf_module.set_error('Please enter a CSV')
            return None
        try:
            table = pd.read_csv(io.StringIO(tablestr), header=header_row)
        except CParserError as e:
            wf_module.set_error(str(e))
            return None

        wf_module.set_ready(notify=False)
        return table


# Utility class: globals defined for user-entered python code
custom_code_globals = {
    '__builtins__': {},  # disallow import etc. (though still not impossible!)
    'str': str,
    'math' : math,
    'pd' : pd,
    'np' : np
}


# ---- Formula ----

class Formula(ModuleImpl):
    def render(wf_module, table):
        formula = wf_module.get_param_string('formula')
        colnames = list(table.columns)
        newcol = pd.Series(np.zeros(len(table)))

        # Catch errors with the formula and display to user
        try:
            code = compile(formula, '<string>', 'eval')

            # Much experimentation went into the form of this loop for good performance.
            # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
            for i,row in enumerate(table.values):
                newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))
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



# ---- RawCode ----

# adds two spaces before every line
def indent_lines(str):
    return '  ' + str.replace('\n', '\n  ');

class RawCode(ModuleImpl):
    def render(wf_module, table):
        code = wf_module.get_param_string('code')

        # turn the user-supplied text into a function declaration
        code = 'def process(table):\n' + indent_lines(code)

        # this is where we will store the function we define
        locals = {}

        # Catch errors with the code and display to user
        try:
            exec(code, custom_code_globals, locals )

        except Exception as e:
            wf_module.set_error(str(e))
            return None

        if not 'process' in locals:
            wf_module.set_error('Problem defining function')
            return None

        out_table = locals['process'](table)
        return out_table


# ---- SelectColumns ----

class SelectColumns(ModuleImpl):
    def render(wf_module, table):
        cols = wf_module.get_param_string('colnames').split(',')
        cols = [c.strip() for c in cols]

        for c in cols:
            if not c in table.columns:
                wf_module.set_error('There is no column named %s' % c)
                return None

        wf_module.set_ready(notify=False)
        newtab = table[cols]
        return newtab

# ---- Chart ----
class Chart(ModuleImpl):
    pass # no render logic, it's all front end




# ---- TextSearch ----
# Returns only those rows which contain the query string in any of the specified columns

class TextSearch(ModuleImpl):
    def render(wf_module, table):
        query = wf_module.get_param_string('query')
        cols = wf_module.get_param_string('colnames').split(',')
        cols = [c.strip() for c in cols]
        case_sensitive = wf_module.get_param_checkbox('casesensitive')
        regex = wf_module.get_param_checkbox('regex')

        if cols == ['']:
            return None     # no columns, no matches

        if query=='':
            return table    # no query, everything matches

        keeprows = None
        for c in cols:
            if not c in table.columns:
                wf_module.set_error('There is no column named %s' % c)
                return None

            kr = table[c].astype(str).str.contains(query, case=case_sensitive, regex=regex)

            # logical OR of all matching columns
            if keeprows is not None:
                keeprows = keeprows | kr
            else:
                keeprows = kr

        newtab = table[keeprows]
        wf_module.set_ready(notify=False)
        return newtab



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
    'loadurl':      LoadURL,
    'pastecsv':     PasteCSV,
    'formula':      Formula,
    'selectcolumns':SelectColumns,
    'rawcode':      RawCode,
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
