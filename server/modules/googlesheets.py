from .moduleimpl import ModuleImpl
from .utils import *
from cjworkbench import google_oauth
from django.http import JsonResponse, HttpResponseBadRequest
import httplib2
import googleapiclient
from googleapiclient.discovery import build
from server.sanitizedataframe import *
import io
import json
import pandas as pd
from pandas.io.common import CParserError
from server.versions import save_fetched_table_if_changed

def get_spreadsheet(sheet_id, owner=False):
    credential = google_oauth.user_to_existing_oauth2_credential(user=owner)
    if not credential:
        return (None, 'Not authorized. Please reconnect to Google Drive.')

    http = httplib2.Http()
    http = credential.authorize(http)
    service = build("drive", "v3", http=http)

    files_request = service.files().export(fileId=sheet_id, mimeType="text/csv")
    try:
        the_file = files_request.execute()
        return (the_file.decode("utf-8"), None)
    except googleapiclient.errors.HttpError as err:
        return (None, str(err))

class GoogleSheets(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        return wf_module.retrieve_fetched_table()

    @staticmethod
    def event(wfmodule, **kwargs):
        file_meta_json = wfmodule.get_param_raw('fileselect', 'custom')
        if not file_meta_json: return
        file_meta = json.loads(file_meta_json)
        sheet_id = file_meta['id']

        if sheet_id:
            owner = wfmodule.workflow.owner
            new_data, error = get_spreadsheet(sheet_id, owner=owner)

            if error:
                table = pd.DataFrame()
            else:
                try:
                    table = pd.read_csv(io.StringIO(new_data))
                    error = ''
                except CParserError as e:
                    table = pd.DataFrame()
                    error = str(e)

            sanitize_dataframe(table)
            save_fetched_table_if_changed(wfmodule, table, error)
