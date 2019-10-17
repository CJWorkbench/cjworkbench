import json
from typing import Any, Dict
import aiohttp
import asyncio
from oauthlib import oauth2
import pandas as pd
from cjwkernel.pandas.types import Tuple, Union
from cjwkernel.pandas.moduleutils import (
    parse_bytesio,
    spooled_data_from_url,
    turn_header_into_first_row,
)


_Secret = Dict[str, Any]


def _generate_google_sheet_url(sheet_id: str) -> str:
    """
    URL to download text/csv from Google Drive.

    This uses the GDrive "export" API.

    Google Content-Type header is broken. According to RFC2616, "Data in
    character sets other than "ISO-8859-1" or its subsets MUST be labeled
    with an appropriate charset value". Google Sheets does not specify a
    charset (implying ISO-8859-1), but the text it serves is utf-8.
    
    So the caller should ignore the content-type Google returns.
    """
    return (
        f"https://www.googleapis.com/drive/v3/files/"
        f"{sheet_id}/export?mimeType=text%2Fcsv"
    )


def _generate_gdrive_file_url(sheet_id: str) -> str:
    """
    URL to download raw bytes from Google Drive.

    This discards Content-Type, including charset. GDrive doesn't know the
    charset anyway.
    """
    return f"https://www.googleapis.com/drive/v3/files/{sheet_id}?alt=media"


async def download_data_frame(
    sheet_id: str, sheet_mime_type: str, oauth2_client: oauth2.Client
) -> Union[pd.DataFrame, str, Tuple[pd.DataFrame, str]]:
    """Download spreadsheet from Google, or return a str error message.

    Arguments decide how the download and parse will occur:

    * If `secret` is not set, return an error.
    * If `sheet_mime_type` is 'application/vnd.google-apps.spreadsheet', use
      GDrive API to _export_ a text/csv, then parse it. Otherwise, use GDrive
      API to _download_ the file, and parse it according to its mime type.
    """
    if sheet_mime_type == "application/vnd.google-apps.spreadsheet":
        url = _generate_google_sheet_url(sheet_id)
        sheet_mime_type = "text/csv"
    else:
        url = _generate_gdrive_file_url(sheet_id)
        # and use the passed sheet_mime_type

    url, headers, _ = oauth2_client.add_token(url, headers={})

    try:
        async with spooled_data_from_url(url, headers) as (blobio, _, __):
            return parse_bytesio(blobio, sheet_mime_type)
    except aiohttp.ClientResponseError as err:
        if err.status == 401:
            return "Invalid credentials. Please reconnect to Google Drive."
        elif err.status == 403:
            return "You chose a file your logged-in user cannot access. Please reconnect to Google Drive or choose a different file."
        elif err.status == 404:
            return "File not found. Please choose a different file."
        else:
            return "GDrive responded with HTTP %d %s" % (err.status, err.message)
    except aiohttp.ClientError as err:
        return "Error during GDrive request: %s" % str(err)
    except asyncio.TimeoutError:
        return "Timeout during GDrive request"


def render(_unused_table, params, *, fetch_result, **kwargs):
    # Must perform header operation here in the event the header checkbox
    # state changes
    if not fetch_result:
        return pd.DataFrame()  # user hasn't fetched yet

    if fetch_result.status == "error":
        return fetch_result.error

    table = fetch_result.dataframe

    has_header: bool = params["has_header"]
    if not has_header:
        table = turn_header_into_first_row(table)

    if fetch_result.error:
        return (table, fetch_result.error)
    else:
        return table


async def fetch(params, *, secrets, **kwargs):
    file_meta = params["file"]
    if not file_meta:
        return None

    # Ignore file_meta['url']. That's for the client's web browser, not for
    # an API request.
    sheet_id = file_meta["id"]
    if not sheet_id:
        return None

    # backwards-compat for old entries without 'mimeType', 2018-06-13
    sheet_mime_type = file_meta.get(
        "mimeType", "application/vnd.google-apps.spreadsheet"
    )

    secret = secrets.get("google_credentials")
    if not secret:
        return "Please connect to Google Drive."
    if "error" in secret:
        assert secret["error"]["id"] == "TODO_i18n"
        return secret["error"]["args"][0]
    assert "secret" in secret
    oauth2_client = oauth2.Client(
        client_id=None,  # unneeded
        token_type=secret["secret"]["token_type"],
        access_token=secret["secret"]["access_token"],
    )

    return await download_data_frame(sheet_id, sheet_mime_type, oauth2_client)


def _migrate_params_v0_to_v1(params):
    """
    v0: `googlefileselect` was a JSON-encoded String.

    v1: `file` is an Optional[Dict[str, str]]
    """
    if params["googlefileselect"]:
        file = json.loads(params["googlefileselect"])
    else:
        file = None
    return {
        "has_header": params["has_header"],
        "version_select": params["version_select"],
        "file": file,
    }


def migrate_params(params):
    if "googlefileselect" in params:
        params = _migrate_params_v0_to_v1(params)
    return params
