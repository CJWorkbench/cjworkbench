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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import cjwparquet
from cjwmodule.http import HttpError, httpfile
from cjwmodule.i18n import I18nMessage, trans
from cjwparse.api import MimeType, parse_file

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


def _parse_content_disposition_filename(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None

    import email.message

    part = email.message.MIMEPart()
    part["Content-Disposition"] = s
    return part.get_filename()


def _parse_url_filename(url: str) -> str:
    return url.split("?", 1)[0].split("/")[-1]


def guess_mime_type_or_none(
    content_type: str, content_disposition: Optional[str], url: str
) -> MimeType:
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

    # No match? Check the filename. This comes from Content-Disposition or,
    # as a fallback, from the URL.
    filename = _parse_content_disposition_filename(
        content_disposition
    ) or _parse_url_filename(url)
    for extension, mime_type in ExtensionMimeTypes.items():
        if filename.endswith(extension):
            return mime_type

    # No match? Check for a known extension in the URL.
    # ".csv" becomes "text/csv".

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
    input_path: Path, errors, output_path: Path, params: Dict[str, Any]
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
            trans(
                "prompt.disableHeaderHandling",
                "Please re-download this file to disable header-row handling",
            )
        ]

    return errors


def _render_file(path: Path, output_path: Path, params: Dict[str, Any]):
    with httpfile.read(path) as (parameters, status_line, headers, body_path):
        content_type = httpfile.extract_first_header(headers, "Content-Type") or ""
        content_disposition = httpfile.extract_first_header(
            headers, "Content-Disposition"
        )

        mime_type = guess_mime_type_or_none(
            content_type, content_disposition, parameters["url"]
        )
        if not mime_type:
            return [
                trans(
                    "error.unhandledContentType",
                    "Server responded with unhandled Content-Type {content_type}. "
                    "Please use a different URL.",
                    {"content_type": content_type},
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
            fetch_result.path,
            [tuple(e.message) for e in fetch_result.errors],
            output_path,
            params,
        )
    elif fetch_result.errors:
        # We've never stored errors+data. If there are errors, assume
        # there's no data.
        output_path.write_bytes(b"")
        return [tuple(e.message) for e in fetch_result.errors]
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
