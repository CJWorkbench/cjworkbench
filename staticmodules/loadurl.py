"""
Fetch data using HTTP, then parse it.

Behavior
--------

1. Fetch: use httpfile.download() to store in httpfile format.
2. Render
    a. If file is in Parquet format, mangle it (has_header) and return it
    b. Otherwise, file is in httpfile format. Extract file contents from
       the data and use HTTP headers to determine charset and file format.
       Return parse result (which may be an error).

File format
-----------

Old versions of loadurl processed during fetch; they produced Parquet files
(v1 or v2, with or without dictionary encoding), and those files must be
supported forevermore. All these files were parsed with `has_header=True` and
types were auto-detected. There is no way to recover the original data.

Newer versions of loadurl (2019-11-01 onwards) store fetched data in "httpfile"
format, which is more akin to actual HTTP traffic.
"""
import asyncio
from pathlib import Path
import re
from typing import Any, Dict, List
from cjwparse import parse_file, MimeType
import cjwparquet
from cjwmodule.http import httpfile, HttpError
from cjwmodule.i18n import I18nMessage


ExtensionMimeTypes = {
    ".xls": MimeType.XLS,
    ".xlsx": MimeType.XLSX,
    ".csv": MimeType.CSV,
    ".tsv": MimeType.TSV,
    ".json": MimeType.JSON,
}


AllowedMimeTypes = list(ExtensionMimeTypes.values())


NonstandardMimeTypes = {
    "application/csv": MimeType.CSV,
    # http://samplecsvs.s3.amazonaws.com/SacramentocrimeJanuary2006.csv
    "application/x-csv": MimeType.CSV,
}


def guess_mime_type_or_none(content_type: str, url: str) -> MimeType:
    """Infer MIME type from Content-Type header or URL, or return None."""
    # First, accept "Content-Type" but clean it: "text/csv; charset=utf-8"
    # becomes "text/csv"
    for mime_type in AllowedMimeTypes:
        if content_type.startswith(mime_type.value) and mime_type != MimeType.TXT:
            return mime_type

    # No match? Then try to "correct" the MIME type.
    # "application/csv; charset=utf-8" becomes "text/csv".
    for nonstandard_mime_type, mime_type in NonstandardMimeTypes.items():
        if content_type.startswith(nonstandard_mime_type):
            return mime_type

    # No match? Check for a known extension in the URL.
    # ".csv" becomes "text/csv".
    for extension, mime_type in ExtensionMimeTypes.items():
        if url.split("?", 1)[0].endswith(extension):
            return mime_type

    # We ignored MimeType.TXT before. Check for it now.
    if content_type.startswith(MimeType.TXT.value):
        return MimeType.TXT

    return None


# https://tools.ietf.org/html/rfc2978 specifies charset regex
# mime-charset-chars = ALPHA / DIGIT /
#        "!" / "#" / "$" / "%" / "&" /
#        "'" / "+" / "-" / "^" / "_" /
#        "`" / "{" / "}" / "~"
_CHARSET_REGEX = re.compile(r";\s*charset=([-!#$%&'+^_`{}~a-zA-Z0-9]+)", re.IGNORECASE)


def guess_charset_or_none(content_type: str) -> str:
    m = _CHARSET_REGEX.match(content_type)
    if m:
        return m.group(1)
    else:
        return None


def _render_deprecated_parquet(
    input_path: Path, errors, output_path: Path, params: Dict[str, Any],
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


def _render_file(path: Path, output_path: Path, params: Dict[str, Any]):
    with httpfile.read(path) as (parameters, status_line, headers, body_path):
        content_type = httpfile.extract_first_header(headers, "Content-Type")

        mime_type = guess_mime_type_or_none(content_type, parameters["url"])
        if not mime_type:
            return [
                (
                    "TODO_i18n",
                    {
                        "text": (
                            "Server responded with unhandled Content-Type %r. "
                            "Please use a different URL."
                        )
                        % content_type
                    },
                    None,
                )
            ]
        maybe_charset = guess_charset_or_none(content_type)

        return parse_file(
            body_path,
            output_path=output_path,
            encoding=maybe_charset,
            mime_type=mime_type,
            has_header=params["has_header"],
        )


def render(arrow_table, params, output_path, *, fetch_result, **kwargs):
    if fetch_result is None:
        # empty table
        output_path.write_bytes(b"")
        return []
    elif fetch_result.path is not None and cjwparquet.file_has_parquet_magic_number(
        fetch_result.path
    ):
        # Deprecated files: we used to parse in fetch() and store the result
        # as Parquet. Now we've lost the original file data, and we need to
        # support our oldest users.
        return _render_deprecated_parquet(
            fetch_result.path, fetch_result.errors, output_path, params
        )
    elif fetch_result.errors:
        # We've never stored errors+data. If there are errors, assume
        # there's no data.
        output_path.write_bytes(b"")
        return [tuple(error.message) for error in fetch_result.errors]
    else:
        assert not fetch_result.errors  # we've never stored errors+data.
        return _render_file(fetch_result.path, output_path, params)


def fetch(params: Dict[str, Any], *, output_path: Path) -> List[I18nMessage]:
    url: str = params["url"].strip()
    mimetypes = ",".join(v.value for v in AllowedMimeTypes)
    headers = [("Accept", mimetypes)]

    try:
        asyncio.run(httpfile.download(url, output_path, headers=headers))
    except HttpError as err:
        return [err.i18n_message]

    return []
