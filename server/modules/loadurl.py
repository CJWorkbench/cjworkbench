from .moduleimpl import ModuleImpl
from server.models import ChangeDataVersionCommand
from server.versions import notify_client_workflow_version_changed
from django.utils import timezone
import csv
import pandas as pd
from pandas.parser import CParserError
from xlrd import XLRDError
import io
import json
import requests
import re

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
        tablestr = wf_module.retrieve_data()
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

        if wfm.status != wfm.ERROR:
            wfm.set_ready(notify=False)

            wfm.last_update_check = timezone.now()
            wfm.save()

            # We are done loading data. See if the saved data is any different.
            # If so create a new data version and switch to it
            new_csv = table.to_csv(index=False) # index=False to prevent pandas from adding an index col
            old_csv = wfm.retrieve_data()
            if new_csv != old_csv:
                version = wfm.store_data(new_csv)
                ChangeDataVersionCommand.create(wfm, version)  # also notifies client
            else:
                # no new data version, but we still want client to update WfModule status and last update check time
                notify_client_workflow_version_changed(wfm.workflow)

