from .moduleimpl import ModuleImpl
import pandas as pd
from pandas.parser import CParserError
from xlrd import XLRDError
import io
import requests
import re
from server.versions import save_fetched_table_if_changed
from server.utils import sanitize_dataframe

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
        return wf_module.retrieve_fetched_table()

    # Load a CSV from file when fetch pressed
    @staticmethod
    def event(wfm, event=None, **kwargs):
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
                # path = wfm.get_param_string('json_path')
                # if len(path)>0:
                #     table_json = parse_json_path(table_json, path)
                table = pd.DataFrame(table_json)

            # except KeyError as e:
            #     wfm.set_error('Bad json path %s' % path)
            #     table = pd.DataFrame([{'result':res.text}])
            #     return

            except ValueError as e:
                wfm.set_error(str(e))
                table = pd.DataFrame([{'result': res.text}])
                return

        elif content_type == "application/octet-stream" and '.xls' in url:
            try:
                table = pd.read_excel(io.BytesIO(res.content))
            except XLRDError as e:
                wfm.set_error(str(e))
                return

        else:
            wfm.set_error('Error fetching %s: unknown content type %s' % (url,content_type))
            return

        if wfm.status != wfm.ERROR:
            wfm.set_ready(notify=False)

            # Change the data version (when new data found) only if this module set to auto update, or user triggered
            auto = wfm.auto_update_data or (event is not None and event.get('type') == "click")

            sanitize_dataframe(table) # ensure all columns are simple types (e.g. nested json to strings)

            # Also notifies client
            save_fetched_table_if_changed(wfm, table, auto_change_version=auto)
