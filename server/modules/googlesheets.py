from .moduleimpl import ModuleImpl
from django.conf import settings
from server.sanitizedataframe import sanitize_dataframe
import io
import json
import pandas as pd
from pandas.io.common import CParserError
from server.versions import save_fetched_table_if_changed
from typing import Any, Dict, Tuple, Optional
from server import oauth
import requests


def get_spreadsheet(
        sheet_id: str,
        secret: Optional[Dict[str,Any]]) -> Tuple[Optional[str], Optional[str]]:
    """HTTP-request, bailing on error or if secret is invalid.

    Return (DataFrame, None) if everything worked.

    Return (None, 'message') if something went wrong.
    """
    if not secret:
        return (None, 'Not authorized. Please connect to Google Drive.')

    service = oauth.OAuthService.lookup_or_none('google_credentials')
    if not service:
        return (None, 'google_credentials not configured. Please restart Workbench with a Google secret.')

    client = service.requests_or_str_error(secret)
    if isinstance(client, str): return (None, client)

    uri = f'https://www.googleapis.com/drive/v3/files/{sheet_id}/export?mimeType=text%2Fcsv'
    try:
        response = client.get(uri)
        body = response.text

        if response.status_code < 200 or response.status_code > 299:
            return (None, f'HTTP {response.status_code} from Google: {body}')
    except requests.RequestException as err:
        return (None, str(err))

    return (body, None)


class GoogleSheets(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        return wf_module.retrieve_fetched_table()

    @staticmethod
    def event(wfmodule, **kwargs):
        file_meta_json = wfmodule.get_param_raw('googlefileselect', 'custom')
        if not file_meta_json: return
        file_meta = json.loads(file_meta_json)
        sheet_id = file_meta['id']
        # Ignore file_meta['url']. That's for the client's web browser, not for
        # an API request.

        if sheet_id:
            secret = wfmodule.get_param_secret_secret('google_credentials')
            new_data, error = get_spreadsheet(sheet_id, secret)

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
