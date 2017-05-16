import pandas as pd
from pandas.parser import CParserError
from xlrd import XLRDError
import csv
import io
import json
import requests
import re
from .moduleimpl import ModuleImpl
from server.versions import bump_workflow_version

# ---- LoadURL ----

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

class LoadURL(ModuleImpl):

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

