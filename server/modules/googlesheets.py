from .moduleimpl import ModuleImpl
from django.conf import settings
from server.sanitizedataframe import sanitize_dataframe
import io
import json
import pandas
from pandas import DataFrame
import pandas.errors
from server.versions import save_fetched_table_if_changed
from typing import Any, Dict, Callable, Optional, Union
from server import oauth
import requests


_Secret = Dict[str,Any]


def _safe_parse(blob: bytes,
                parser: Callable[[bytes], DataFrame]) -> Union[DataFrame, str]:
    """Run the given parser, or return the error as a string.

    Empty dataset is not an error: it is just an empty dataset.
    """
    try:
        return parser(blob)
    except pandas.errors.EmptyDataError:
        return DataFrame()
    except pandas.errors.ParserError as err:
        return str(err)


def _parse_csv(blob: bytes) -> Union[DataFrame, str]:
    """Build a DataFrame or str error message.

    Peculiarities:

    * The file encoding is UTF-8. This is correct when we export a CSV from
      Google Sheets (type 'document') -- despite Google's incorrect
      Content-Type header. But when we download a 'file' CSV from Google, we
      don't know the encoding.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    return pandas.read_csv(io.BytesIO(blob), encoding='utf-8')


def _parse_tsv(blob: bytes) -> Union[DataFrame, str]:
    """Build a DataFrame or str error message.

    Peculiarities:

    * The file encoding is UTF-8, always. When we download a 'file' TSV from
      Google, we don't know the encoding. (TODO consider chardet)
    * Data types. This is a TSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    return pandas.read_table(io.BytesIO(blob), encoding='utf-8')


def _parse_xlsx(blob: bytes) -> Union[DataFrame, str]:
    """Build a DataFrame or str error message.
    """
    return pandas.read_excel(io.BytesIO(blob))


_parse_xls = _parse_xlsx


def _build_requests_session(secret: _Secret) -> Union[requests.Session,str]:
    """Prepare a Requests session, so caller can then call
    `session.get(url)`.
    """
    service = oauth.OAuthService.lookup_or_none('google_credentials')
    if not service:
        return 'google_credentials not configured. Please restart Workbench with a Google secret.'

    session = service.requests_or_str_error(secret)
    return session # even if it's an error


def _download_bytes(session: requests.Session, url: str) -> Union[bytes,str]:
    """Download bytes from `url` or return a str error message.

    This discards Content-Type, including charset. GDrive doesn't know the
    charset anyway.
    """
    try:
        response = session.get(url)

        if response.status_code < 200 or response.status_code > 299:
            return f'HTTP {response.status_code} from Google: {response.text}'

        return response.content
    except requests.RequestException as err:
        return str(err)


def _download_google_sheet(session: requests.Session,
                           sheet_id: str) -> Union[bytes,str]:
    """Download a Google Sheet as utf-8 CSV, or return a str error message.

    This uses the GDrive "export" API.
    """
    # Google Content-Type header is broken. According to RFC2616, "Data in
    # character sets other than "ISO-8859-1" or its subsets MUST be labeled
    # with an appropriate charset value". Google Sheets does not specify a
    # charset (implying ISO-8859-1), but the text it serves is utf-8.
    #
    # So we ignore the content-type.
    url = f'https://www.googleapis.com/drive/v3/files/{sheet_id}/export?mimeType=text%2Fcsv'
    return _download_bytes(session, url)


def _download_gdrive_file(session: requests.Session,
                          sheet_id: str) -> Union[bytes,str]:
    """Download bytes from Google Drive, or return a str error message.

    This discards Content-Type, including charset. GDrive doesn't know the
    charset anyway.
    """
    url = f'https://www.googleapis.com/drive/v3/files/{sheet_id}?alt=media'
    return _download_bytes(session, url)


def download_data_frame(sheet_id: str, sheet_mime_type: str,
                        secret: Optional[_Secret]) -> Union[DataFrame, str]:
    """Download spreadsheet from Google, or return a str error message.

    Arguments decide how the download and parse will occur:

    * If `secret` is not set, return an error.
    * If `sheet_mime_type` is 'application/vnd.google-apps.spreadsheet', use
      GDrive API to _export_ a text/csv, then parse it. Otherwise, use GDrive
      API to _download_ the file, and parse it according to its mime type.
    """
    if not secret:
        return 'Not authorized. Please connect to Google Drive.'

    session = _build_requests_session(secret)
    if isinstance(session, str): return session

    if sheet_mime_type == 'application/vnd.google-apps.spreadsheet':
        blob = _download_google_sheet(session, sheet_id)
        sheet_mime_type = 'text/csv'
    else:
        blob = _download_gdrive_file(session, sheet_id)
    if isinstance(blob, str): return blob

    parser = _Parsers[sheet_mime_type]
    return _safe_parse(blob, parser)


_Parsers = {
    'text/csv': _parse_csv,
    'text/tab-separated-values': _parse_tsv,
    'application/vnd.ms-excel': _parse_xls,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': _parse_xlsx,
}


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
        # backwards-compat for old entries without 'mimeType', 2018-06-13
        sheet_mime_type = file_meta.get('mimeType', 'application/vnd.google-apps.spreadsheet')

        # Ignore file_meta['url']. That's for the client's web browser, not for
        # an API request.

        if sheet_id:
            secret = wfmodule.get_param_secret_secret('google_credentials')
            result = download_data_frame(sheet_id, sheet_mime_type, secret)
            if isinstance(result, str):
                table, error = (DataFrame(), result)
            else:
                table, error = (result, '')
                sanitize_dataframe(table)

            save_fetched_table_if_changed(wfmodule, table, error)
