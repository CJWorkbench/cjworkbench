import asyncio
import json
from pathlib import Path
import os
from typing import Any, Dict, List, Optional
from oauthlib import oauth2
from cjwkernel.pandas.http import httpfile
from cjwkernel.pandas.parse import MimeType, parse_file
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.pandas import moduleutils
from cjwkernel import parquet
from cjwkernel.types import (
    ArrowTable,
    FetchResult,
    I18nMessage,
    RenderError,
    RenderResult,
)


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
    return FetchResult(output_path, [RenderError(I18nMessage.TODO_i18n(message))])


async def do_download(
    sheet_id: str, sheet_mime_type: str, oauth2_client: oauth2.Client, output_path: Path
) -> FetchResult:
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
    except httpfile.HttpError.ClientResponseError as err:
        cause = err.__cause__
        if cause.status == 401:
            return TODO_i18n_fetch_error(
                output_path, "Invalid credentials. Please reconnect to Google Drive."
            )
        elif cause.status == 403:
            return TODO_i18n_fetch_error(
                output_path,
                "You chose a file your logged-in user cannot access. Please reconnect to Google Drive or choose a different file.",
            )
        elif cause.status == 404:
            return TODO_i18n_fetch_error(
                output_path, "File not found. Please choose a different file."
            )
        else:
            return TODO_i18n_fetch_error(
                output_path,
                "GDrive responded with HTTP %d %s" % (cause.status, cause.message),
            )
    except httpfile.HttpError as err:
        os.truncate(output_path, 0)
        return FetchResult(output_path, errors=[RenderError(err.i18n_message)])

    return FetchResult(output_path)


def _render_deprecated_parquet(
    input_path: Path,
    errors: List[RenderError],
    output_path: Path,
    params: Dict[str, Any],
) -> RenderResult:
    parquet.convert_parquet_file_to_arrow_file(input_path, output_path)
    result = RenderResult(
        ArrowTable.from_arrow_file_with_inferred_metadata(output_path), errors
    )

    if result.table.metadata.n_rows > 0 and not params["has_header"]:
        pandas_result = ProcessResult.from_arrow(result)
        dataframe = moduleutils.turn_header_into_first_row(pandas_result.dataframe)
        return ProcessResult(dataframe).to_arrow(output_path)

    return result


def _calculate_mime_type(content_type: str) -> MimeType:
    for mime_type in MimeType:
        if content_type.startswith(mime_type.value):
            return mime_type
    # If we get here, we downloaded a MIME type we couldn't handle ... even
    # though we explicitly requested a MIME type we can handle. Undefined
    # behavior.
    raise RuntimeError("Unsupported content_type %s" % content_type)


def _render_file(path: Path, params: Dict[str, Any], output_path: Path):
    with httpfile.read(path) as (body_path, url, headers):
        content_type = httpfile.extract_first_header_from_str(headers, "Content-Type")
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


def render_arrow(
    table, params, tab_name, fetch_result: Optional[FetchResult], output_path: Path
) -> RenderResult:
    # Must perform header operation here in the event the header checkbox
    # state changes
    if fetch_result is None:
        # empty table
        return RenderResult(ArrowTable())
    elif fetch_result.path is not None and parquet.file_has_parquet_magic_number(
        fetch_result.path
    ):
        # Deprecated files: we used to parse in fetch() and store the result
        # as Parquet. Now we've lost the original file data, and we need to
        # support our oldest users.
        #
        # In this deprecated format, parse errors were written as
        # fetch_result.errors.
        return _render_deprecated_parquet(
            fetch_result.path, fetch_result.errors, output_path, params
        )
    elif fetch_result.errors:
        # We've never stored errors+data. If there are errors, assume
        # there's no data.
        return RenderResult(ArrowTable(), fetch_result.errors)
    else:
        assert not fetch_result.errors  # we've never stored errors+data.
        return _render_file(fetch_result.path, params, output_path)


def fetch_arrow(
    params: Dict[str, Any],
    secrets: Dict[str, Any],
    last_fetch_result,
    input_table_parquet_path,
    output_path: Path,
) -> FetchResult:
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
        return TODO_i18n_fetch_error(output_path, "Please connect to Google Drive.")
    if "error" in secret:
        return FetchResult(
            output_path, errors=[RenderError(I18nMessage.from_dict(secret["error"]))]
        )
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
