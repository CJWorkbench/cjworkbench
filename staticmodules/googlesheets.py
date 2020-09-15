import asyncio
import json
from pathlib import Path
import os
from typing import Any, Dict, List
from oauthlib import oauth2
from cjwmodule.http import httpfile, HttpError
from cjwmodule.i18n import I18nMessage
import cjwparquet
from cjwparse.api import MimeType, parse_file


_Secret = Dict[str, Any]


GDRIVE_API_URL = "https://www.googleapis.com/drive/v3"  # unit tests override this
SSL_CONTEXT = None  # unit tests override this


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
    return f"{GDRIVE_API_URL}/files/{sheet_id}/export?mimeType=text%2Fcsv"


def _generate_gdrive_file_url(sheet_id: str) -> str:
    """
    URL to download raw bytes from Google Drive.

    This discards Content-Type, including charset. GDrive doesn't know the
    charset anyway.
    """
    return f"{GDRIVE_API_URL}/files/{sheet_id}?alt=media"


def TODO_i18n_fetch_error(output_path: Path, message: str):
    os.truncate(output_path, 0)
    return [I18nMessage("TODO_i18n", {"text": message}, None)]


async def do_download(
    sheet_id: str, sheet_mime_type: str, oauth2_client: oauth2.Client, output_path: Path
) -> List[I18nMessage]:
    """
    Download spreadsheet from Google.

    If `sheet_mime_type` is 'application/vnd.google-apps.spreadsheet', use
    GDrive API to _export_ a text/csv. Otherwise, use GDrive API to _download_
    the file.
    """
    if sheet_mime_type == "application/vnd.google-apps.spreadsheet":
        url = _generate_google_sheet_url(sheet_id)
        sheet_mime_type = "text/csv"
    else:
        url = _generate_gdrive_file_url(sheet_id)
        # and use the passed sheet_mime_type

    url, headers, _ = oauth2_client.add_token(url, headers={})

    try:
        await httpfile.download(url, output_path, headers=headers, ssl=SSL_CONTEXT)
    except HttpError.NotSuccess as err:
        response = err.response
        if response.status_code == 401:
            return TODO_i18n_fetch_error(
                output_path, "Invalid credentials. Please reconnect to Google Drive."
            )
        elif response.status_code == 403:
            return TODO_i18n_fetch_error(
                output_path,
                "You chose a file your logged-in user cannot access. Please reconnect to Google Drive or choose a different file.",
            )
        elif response.status_code == 404:
            return TODO_i18n_fetch_error(
                output_path, "File not found. Please choose a different file."
            )
        else:
            return [err.i18n_message]
    except HttpError as err:
        # HACK: *err.i18n_message because i18n_message is a tuple
        # compatible with I18nMessage() ctor
        os.truncate(output_path, 0)
        return [err.i18n_message]

    return []


def _render_deprecated_parquet(
    input_path: Path, errors: List[Any], output_path: Path, params: Dict[str, Any]
) -> List[I18nMessage]:
    cjwparquet.convert_parquet_file_to_arrow_file(input_path, output_path)
    if params["has_header"]:
        # In the deprecated parquet format, we _always_ parsed the header
        pass
    else:
        # We used to have a "moduleutils.turn_header_into_first_row()" but it
        # was broken by design (what about types???) and it was rarely used.
        # Let's not maintain it any longer.
        errors += [
            I18nMessage(
                "TODO_i18n",
                {"text": "Please re-download this file to disable header-row handling"},
                None,
            )
        ]

    return errors


def _calculate_mime_type(content_type: str) -> MimeType:
    for mime_type in MimeType:
        if content_type.startswith(mime_type.value):
            return mime_type
    # If we get here, we downloaded a MIME type we couldn't handle ... even
    # though we explicitly requested a MIME type we can handle. Undefined
    # behavior.
    raise RuntimeError("Unsupported content_type %s" % content_type)


def _render_file(path: Path, params: Dict[str, Any], output_path: Path):
    with httpfile.read(path) as (parameters, status_line, headers, body_path):
        content_type = httpfile.extract_first_header(headers, "Content-Type")
        mime_type = _calculate_mime_type(content_type)
        # Ignore Google-reported charset. Google's headers imply latin-1 when
        # their data is utf-8.
        return parse_file(
            body_path,
            encoding=None,
            mime_type=mime_type,
            has_header=params["has_header"],
            output_path=output_path,
        )


def render(arrow_table, params, output_path, *, fetch_result, **kwargs):
    # Must perform header operation here in the event the header checkbox
    # state changes
    if fetch_result is None:
        # empty table
        return []
    elif fetch_result.path is not None and cjwparquet.file_has_parquet_magic_number(
        fetch_result.path
    ):
        # Deprecated files: we used to parse in fetch() and store the result
        # as Parquet. Now we've lost the original file data, and we need to
        # support our oldest users.
        #
        # In this deprecated format, parse errors were written as
        # fetch_result.errors.
        return _render_deprecated_parquet(
            fetch_result.path,
            [tuple(e.message) for e in fetch_result.errors],
            output_path,
            params,
        )
    elif fetch_result.errors:
        # We've never stored errors+data. If there are errors, assume
        # there's no data.
        #
        # We've never stored errors with quick-fixes
        return [tuple(e.message) for e in fetch_result.errors]
    else:
        assert not fetch_result.errors  # we've never stored errors+data.
        return _render_file(fetch_result.path, params, output_path)


def fetch(
    params: Dict[str, Any], *, secrets: Dict[str, Any], output_path: Path
) -> List[I18nMessage]:
    file_meta = params["file"]
    if not file_meta:
        return TODO_i18n_fetch_error(output_path, "Please choose a file")

    # Ignore file_meta['url']. That's for the client's web browser, not for
    # an API request.
    sheet_id = file_meta["id"]
    if not sheet_id:
        # [adamhooper, 2019-12-06] has this ever happened?
        return TODO_i18n_fetch_error(output_path, "Please choose a file")

    # backwards-compat for old entries without 'mimeType', 2018-06-13
    sheet_mime_type = file_meta.get(
        "mimeType", "application/vnd.google-apps.spreadsheet"
    )

    secret = secrets.get("google_credentials")
    if not secret:
        return TODO_i18n_fetch_error(output_path, "Please connect to Google Drive.")
    if "error" in secret:
        return [I18nMessage(**secret["error"])]
    assert "secret" in secret
    oauth2_client = oauth2.Client(
        client_id=None,  # unneeded
        token_type=secret["secret"]["token_type"],
        access_token=secret["secret"]["access_token"],
    )

    return asyncio.run(
        do_download(sheet_id, sheet_mime_type, oauth2_client, output_path)
    )


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
