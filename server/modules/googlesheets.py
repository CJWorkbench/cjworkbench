import io
from typing import Any, Dict, Optional, Union
import pandas as pd
import requests
from cjworkbench.types import ProcessResult
from server import oauth
from .utils import parse_bytesio, turn_header_into_first_row, parse_json_param


_Secret = Dict[str, Any]


def _build_requests_session(secret: _Secret) -> Union[requests.Session, str]:
    """Prepare a Requests session, so caller can then call
    `session.get(url)`.
    """
    service = oauth.OAuthService.lookup_or_none('google_credentials')
    if not service:
        return (
            'google_credentials not configured. '
            'Please restart Workbench with a Google secret.'
        )

    session = service.requests_or_str_error(secret)
    return session  # even if it's an error


def _download_bytes(session: requests.Session, url: str) -> Union[bytes, str]:
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
                           sheet_id: str) -> Union[bytes, str]:
    """Download a Google Sheet as utf-8 CSV, or return a str error message.

    This uses the GDrive "export" API.
    """
    # Google Content-Type header is broken. According to RFC2616, "Data in
    # character sets other than "ISO-8859-1" or its subsets MUST be labeled
    # with an appropriate charset value". Google Sheets does not specify a
    # charset (implying ISO-8859-1), but the text it serves is utf-8.
    #
    # So we ignore the content-type.
    url = (
        f'https://www.googleapis.com/drive/v3/files/'
        f'{sheet_id}/export?mimeType=text%2Fcsv'
    )
    return _download_bytes(session, url)


def _download_gdrive_file(session: requests.Session,
                          sheet_id: str) -> Union[bytes, str]:
    """Download bytes from Google Drive, or return a str error message.

    This discards Content-Type, including charset. GDrive doesn't know the
    charset anyway.
    """
    url = f'https://www.googleapis.com/drive/v3/files/{sheet_id}?alt=media'
    return _download_bytes(session, url)


def download_data_frame(sheet_id: str, sheet_mime_type: str,
                        secret: Optional[_Secret]) -> ProcessResult:
    """Download spreadsheet from Google, or return a str error message.

    Arguments decide how the download and parse will occur:

    * If `secret` is not set, return an error.
    * If `sheet_mime_type` is 'application/vnd.google-apps.spreadsheet', use
      GDrive API to _export_ a text/csv, then parse it. Otherwise, use GDrive
      API to _download_ the file, and parse it according to its mime type.
    """
    if not secret:
        return ProcessResult(
            error='Not authorized. Please connect to Google Drive.'
        )

    session = _build_requests_session(secret)
    if isinstance(session, str):
        return ProcessResult(error=session)

    if sheet_mime_type == 'application/vnd.google-apps.spreadsheet':
        blob = _download_google_sheet(session, sheet_id)
        sheet_mime_type = 'text/csv'
    else:
        blob = _download_gdrive_file(session, sheet_id)
    if isinstance(blob, str):
        return ProcessResult(error=blob)

    return parse_bytesio(io.BytesIO(blob), sheet_mime_type)


def render(_unused_table, params, *, fetch_result, **kwargs):
    # Must perform header operation here in the event the header checkbox
    # state changes
    if not fetch_result:
        return pd.DataFrame()  # user hasn't fetched yet

    if fetch_result.status == 'error':
        return fetch_result.error

    table = fetch_result.dataframe

    has_header: bool = params['has_header']
    if not has_header:
        table = turn_header_into_first_row(table)

    if fetch_result.error:
        return (table, fetch_result.error)
    else:
        return table


def fetch(params, **kwargs):  # TODO make async
    file_meta = parse_json_param(params['googlefileselect'])
    if not file_meta:
        return ProcessResult()

    sheet_id = file_meta['id']
    # backwards-compat for old entries without 'mimeType', 2018-06-13
    sheet_mime_type = file_meta.get(
        'mimeType',
        'application/vnd.google-apps.spreadsheet'
    )

    # Ignore file_meta['url']. That's for the client's web browser, not for
    # an API request.

    if sheet_id:
        secret = (params['google_credentials'] or {}).get('secret')
        result = download_data_frame(sheet_id, sheet_mime_type, secret)
        result.truncate_in_place_if_too_big()
        return result
    else:
        return ProcessResult()
