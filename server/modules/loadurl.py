from .moduleimpl import ModuleImpl
from collections import OrderedDict
import pandas as pd
from pandas.io.common import CParserError
from xlrd import XLRDError
import io
import requests
import json
from server.versions import save_fetched_table_if_changed
from server.sanitizedataframe import sanitize_dataframe
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

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
        url = wfm.get_param_string('url').strip()

        validate = URLValidator()
        try:
            validate(url)
        except ValidationError:
            wfm.set_error('That doesn''t seem to be a valid URL')
            return

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()

        excel_types = ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
        csv_types = ['text/csv']
        json_types = ['application/json']
        mimetypes = ','.join(excel_types + csv_types + json_types)

        try:
            res = requests.get(url, headers = {'accept': mimetypes})
        except requests.exceptions.ConnectionError:
            wfm.set_error('Could not connect to server')
            return

        if res.status_code != requests.codes.ok:
            wfm.set_error('Error %s fetching url' % str(res.status_code))
            return

        # get content type, ignoring charset for now
        content_type = res.headers.get('content-type').split(';')[0]

        if content_type in csv_types:
            try:
                table = pd.read_csv(io.StringIO(res.text))
            except CParserError as e:
                wfm.set_error(str(e))
                table = pd.DataFrame([{'result':res.text}])

        elif content_type in excel_types:
            try:
                table = pd.read_excel(io.BytesIO(res.content))
            except XLRDError as e:
                wfm.set_error(str(e))
                return

        elif content_type in json_types:
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
            save_fetched_table_if_changed(wfm, table, '')
