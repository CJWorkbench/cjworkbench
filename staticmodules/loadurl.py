r"""
Fetch data using HTTP, then parse it.

Behavior
--------

1. Fetch
    a. Perform an HTTP request and log traffic (gzipped) to output_file
    b. If the server responds with a redirect, truncate output_file and restart
    c. If there's an error or timeout, truncate output_file and return error
2. Render
    a. If file is in Parquet format, mangle it (has_header) and return it
    b. Otherwise, file is a gzipped HTTP traffic log. Extract file contents from
       the data and use HTTP headers to determine charset and file format.
       Return parse result (which may be an error).

File format
-----------

Old versions of loadurl processed during fetch; they produced Parquet files
(v1 or v2, with or without dictionary encoding), and those files must be
supported forevermore. All these files were parsed with `has_header=True` and
types were auto-detected. There is no way to recover the original data.

The new format is simpler. In case of success, a special HTTP log is written to
a _gzipped_ file:

    https://example.com/test.csv\r\n
    200 OK\r\n
    Response-Header-1: X\r\n
    Response-Header-2: Y\r\n
    \r\n
    All body bytes

`Transfer-Encoding`, `Content-Encoding` and `Content-Length` headers are
renamed `Cjw-Original-Transfer-Encoding`, `Cjw-Original-Content-Encoding`
and `Cjw-Original-Content-Length`. (The body in the HTTP log is dechunked
and decompressed, because Python's ecosystem doesn't have nice options for
storing raw HTTP traffic and dechunking from a file.)

The URL is UTF-8-encoded; status is ASCII-encoded; headers are latin1-encoded;
the body is raw. (Rationale: we wrote URL ourselves; status and headers are
exactly what the server sent.)

In case of redirect, only the last request is logged.
"""
import asyncio
import gzip
from pathlib import Path
import re
import shutil
from typing import Optional, Union
import aiohttp  # for consistency with other Workbench modules
from cjwkernel.pandas import moduleutils
from cjwkernel.pandas.parse_util import parse_bytesio
from cjwkernel.pandas.types import ProcessResult  # deprecated
from cjwkernel.types import FetchResult
from cjwkernel.util import tempfile_context


ExtensionMimeTypes = {
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
}


AllowedMimeTypes = list(ExtensionMimeTypes.values())


NonstandardMimeTypes = {
    "application/csv": "text/csv",
    # http://samplecsvs.s3.amazonaws.com/SacramentocrimeJanuary2006.csv
    "application/x-csv": "text/csv",
}


def guess_mime_type_or_none(content_type: str, url: str) -> str:
    """Infer MIME type from Content-Type header or URL, or return None."""
    # First, accept "Content-Type" but clean it: "text/csv; charset=utf-8"
    # becomes "text/csv"
    for mime_type in AllowedMimeTypes:
        if content_type.startswith(mime_type):
            return mime_type

    # No match? Then try to "correct" the MIME type.
    # "application/csv; charset=utf-8" becomes "text/csv".
    for nonstandard_mime_type, mime_type in NonstandardMimeTypes.items():
        if content_type.startswith(nonstandard_mime_type):
            return mime_type

    # No match? Check for a known extension in the URL.
    # ".csv" becomes "text/csv".
    for extension, mime_type in ExtensionMimeTypes.items():
        if extension in url:
            return mime_type

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


def _render_deprecated_parquet(fetch_result: ProcessResult, params):
    if fetch_result.error:
        # Error means no data, always.
        return fetch_result.error

    table = fetch_result.dataframe
    has_header: bool = params["has_header"]
    if not has_header and len(table) >= 1:
        table = moduleutils.turn_header_into_first_row(table)
    return table


def _render_file(path: Path, params):
    with tempfile_context(prefix="body-") as tf:
        # Parse file into headers + tempfile
        with path.open("rb") as f:
            with gzip.GzipFile(mode="rb", fileobj=f) as zf:
                # read URL (line 1)
                url = zf.readline().decode("utf-8").strip()
                # read and skip status (line 2)
                zf.readline()

                # Read headers and find key values
                # (Just content-type matters for now; but we must read all
                # headers to arrive at the body.)
                content_type = ""
                while True:
                    line = zf.readline().decode("latin1")
                    if not line.strip():
                        # We just read the last line. The rest is body!
                        break
                    else:
                        # Assume header is well-formed: otherwise we wouldn't have
                        # written it to the file
                        header, value = line.split(":", 1)
                        value = value.strip()
                        if header.upper() == "CONTENT-TYPE":
                            content_type = value

                # Read body
                with tf.open("wb") as body_f:
                    shutil.copyfileobj(zf, body_f)

        mime_type = guess_mime_type_or_none(content_type, url)
        if not mime_type:
            return (
                "Server responded with unhandled Content-Type %r."
                "Please use a different URL."
            ) % content_type
        maybe_charset = guess_charset_or_none(content_type)

        with tf.open("rb") as bytesio:
            return parse_bytesio(
                bytesio, maybe_charset, mime_type, params["has_header"]
            )


def render(table, params, *, fetch_result: Optional[Union[FetchResult, ProcessResult]]):
    if fetch_result is None:
        return table  # no-op
    elif isinstance(fetch_result, ProcessResult):
        # This includes empty file, which Workbench treats as ProcessResult
        # with empty dataframe.
        return _render_deprecated_parquet(fetch_result, params)
    else:
        assert not fetch_result.errors  # we've never stored errors+data.
        return _render_file(fetch_result.path, params)


async def fetch(params, *, output_path: Path) -> Union[Path, str]:
    url: str = params["url"].strip()

    mimetypes = ",".join(AllowedMimeTypes)
    headers = {"Accept": mimetypes}
    timeout = aiohttp.ClientTimeout(total=5 * 60, connect=30)

    try:
        async with moduleutils.spooled_data_from_url(url, headers, timeout) as (
            bytesio,
            headers,
            charset,
        ):
            # This shouldn't be a context manager. Oh well. Ignore the fact
            # that bytesio is backed by a file. It's safe to read the file
            # after we exit the context and the file is deleted.
            pass
    except asyncio.TimeoutError:
        output_path.truncate()
        return f"Timeout fetching {url}"
    except aiohttp.InvalidURL:
        return f"Invalid URL"
    except aiohttp.TooManyRedirects:
        return "The server redirected us too many times. Please try a different URL."
    except aiohttp.ClientResponseError as err:
        return "Error from server: %d %s" % (err.status, err.message)
    except aiohttp.ClientError as err:
        return str(err)

    # The following shouldn't ever error.
    with output_path.open("wb") as f:
        # set gzip mtime=0 so we can write the exact same file given the exact
        # same data. (This helps with testing and versioning.)
        with gzip.GzipFile(mode="wb", filename="", fileobj=f, mtime=0) as zf:
            # Write URL -- original URL, not redirected URL
            zf.write(url.encode("utf-8") + b"\r\n")
            # Write status line -- INCORRECT but oh well
            zf.write(b"200 OK\r\n")
            # Write response headers.
            #
            # Ideally we'd be using raw headers. But moduleutils gives
            # parsed headers. Let's not bother with purity: just
            # re-encode the parsed headers.
            for k, v in headers.items():
                # bytesio is already dechunked and decompressed. Mangle
                # these headers to make file consistent with itself.
                if k.lower() in {
                    "transfer-encoding",
                    "content-encoding",
                    "content-length",
                }:
                    k = "Cjw-Original-" + k
                elif k.lower() not in {"content-type", "content-disposition", "server"}:
                    # Skip writing most headers. This is a HACK: we skip the
                    # `Date` header so fetcher will see a byte-for-byte
                    # identical output file given byte-for-byte identical
                    # input. That will convince fetcher to ignore the result.
                    # See `fetcher.versions`. TODO redefine "versions" and
                    # revisit this logic: the user probably _expects_ us to
                    # store headers every fetch, though body may not change.
                    continue
                # There's no way to put \r\n in an HTTP header name or value.
                # Good thing: if a server could do that, this file format would
                # be unreadable.
                assert "\n" not in k and "\n" not in v
                zf.write(f"{k}: {v}\r\n".encode("latin1"))
            zf.write(b"\r\n")

            # Write body
            shutil.copyfileobj(bytesio, zf)
    return output_path
