from .moduleimpl import ModuleImpl
from collections import OrderedDict
import pandas as pd
from pandas.io.common import CParserError
from xlrd import XLRDError
import io
import requests
import json
from server.versions import save_fetched_table_if_changed
from server.utils import sanitize_dataframe

# ---- LoadURL ----

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
                json_string = res.text

                table = pd.DataFrame(json.loads(json_string, object_pairs_hook=OrderedDict)) # OrderedDict otherwise cols get sorted)

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
