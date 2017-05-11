# Module dispatch table and implementations
#from server.models import Module, WfModule
from django.conf import settings
import pandas as pd
import numpy as np
from pandas.parser import CParserError
from xlrd import XLRDError
from twarc import Twarc
import re
import requests
import io
import os
import csv
import json
import math
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

# Walks down through a dict through keys and arrays
# e.g. "Results.series[0].data" -> jsondict['Results']['Series'][0]['data']
def parse_json_path(d, path):
    if path == '':
        return d

    pattern = re.compile('([^\[]+)\[([0-9]+)\]$') # 'key[8]' -> 'key','8'

    # walk down keys and arrays
    for p in path.split('.'):
        m = pattern.match(p)
        if m:
            d = d[m.group(1)]           # d['key']
            d = d[int(m.group(2))]      # d[8]
        else:
            d = d[p]

    return d

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
        table = None

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()
        url = wfm.get_param_string('url')

        mimetypes = 'application/json, text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        res = requests.get(url, headers = {'accept': mimetypes})

        if res.status_code != requests.codes.ok:
            wfm.set_error('Error %s fetching url' % str(res.status_code))
            return

        # get content type, ignoring charset for now
        content_type = res.headers.get('content-type').split(';')[0]

        if content_type == 'text/csv':
            try:
                table = pd.read_csv(io.StringIO(res.text))
            except CParserError as e:
                wfm.set_error(str(e))
                table = pd.DataFrame([{'result':res.text}])

        elif content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            try:
                table = pd.read_excel(io.BytesIO(res.content))
            except XLRDError as e:
                wfm.set_error(str(e))
                return

        elif content_type == 'application/json':
            try:
                table_json = res.json()
                path = wfm.get_param_string('json_path')
                if len(path)>0:
                    table_json = parse_json_path(table_json, path)
                table = pd.DataFrame(table_json)

            except KeyError as e:
                wfm.set_error('Bad json path %s' % path)
                table = pd.DataFrame([{'result':res.text}])
                return

            except ValueError as e:
                wfm.set_error(str(e))
                table = pd.DataFrame([{'result': res.text}])
                return

        else:
            wfm.set_error('Error fetching %s: unknown content type %s' % (url,content_type))
            return

        # we are done. save fetched data, notify of changes to the workflow, reset status
        wfm.store_text('csv', table.to_csv(index=False))      # index=False to prevent pandas from adding an index col

        if wfm.status != wfm.ERROR:
            wfm.set_ready(notify=False)
            bump_workflow_version(wfm.workflow)


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


# ---- Twitter ----

class Twitter(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        tablestr = wf_module.retrieve_text('csv')
        if (tablestr != None) and (len(tablestr) > 0):
            return pd.read_csv(io.StringIO(tablestr))
        else:
            return None


    # Load specified user's timeline
    @staticmethod
    def event(parameter, e):
        wfm = parameter.wf_module
        table = None

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()
        user = wfm.get_param_string('user')

        consumer_key = os.environ['CJW_TWITTER_CONSUMER_KEY']
        consumer_secret = os.environ['CJW_TWITTER_CONSUMER_SECRET']
        access_token = os.environ['CJW_TWITTER_ACCESS_TOKEN']
        access_token_secret = os.environ['CJW_TWITTER_ACCESS_TOKEN_SECRET']

        tw = Twarc(consumer_key, consumer_secret, access_token, access_token_secret)
        tweetsgen = tw.timeline(screen_name=user)

        cols = ['id', 'created_at', 'text', 'in_reply_to_screen_name', 'in_reply_to_status_id', 'retweeted', 'retweet_count', 'favorited', 'favorite_count', 'source']
        tweets = [ [t[x] for x in cols] for t in tweetsgen]
        table = pd.DataFrame(tweets, columns=cols)
        wfm.store_text('csv', table.to_csv(index=False))  # index=False to prevent pandas from adding an index col

        wfm.set_ready(notify=False)
        bump_workflow_version(wfm.workflow)


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
    'selectcolumns':SelectColumns,
    'rawcode':      RawCode,
    'simplechart':  Chart,
    'twitter':      Twitter,

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
