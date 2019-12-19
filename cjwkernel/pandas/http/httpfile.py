r"""
Fetch data using HTTP, then parse it.

Behavior
--------

a. Perform an HTTP request and log traffic (gzipped) to output_file
b. If the server responds with a redirect, truncate output_file and restart
c. If there's an error or timeout, truncate output_file and raise error

File format
-----------

In case of success, a special HTTP log is written to a *gzipped* file:

    {"url":"https://example.com/test.csv"}\r\n
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

The params in the first line are UTF-8-encoded with no added whitespace
(so "\r\n" cannot appear); status is ASCII-encoded; headers are
latin1-encoded; the body is raw. (Rationale: each encoding is the content's
native encoding.)

SECURITY: we don't store the request HTTP headers, because they may contain
OAuth tokens or API keys.

Rationale for storing params: it avoids a race in which we render with new
params but an old fetch result. We only store the "fetch params" ("url"),
not the "render params" ("has_header"), so the file is byte-for-byte identical
when we fetch an unchanged URL with new render params.

In case of redirect, only the last request is logged.
"""

import asyncio
import contextlib
import json
import gzip
from pathlib import Path
import shutil
import ssl
from typing import ContextManager, Dict, BinaryIO, Optional, Tuple
import aiohttp
from .errors import HttpError
from .. import moduleutils
from cjwkernel.util import tempfile_context


__all__ = ["read", "write", "download", "extract_first_header_from_str"]


def write(f: BinaryIO, url: str, headers: Dict[str, str], body: BinaryIO) -> None:
    """
    Write httpfile-formatted data to `f`.

    This module's docstring describes the file format.
    """
    # set gzip mtime=0 so we can write the exact same file given the exact
    # same data. (This helps with testing and versioning.)
    with gzip.GzipFile(mode="wb", filename="", fileobj=f, mtime=0) as zf:
        # Write URL -- original URL, not redirected URL
        zf.write(
            json.dumps(
                {"url": url},  # SECURITY: don't store "headers" secrets
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\r\n"
        )
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
            if k.lower() in {"transfer-encoding", "content-encoding", "content-length"}:
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
        shutil.copyfileobj(body, zf)


async def download(
    url: str,
    output_path: Path,
    *,
    headers: Dict[str, str] = {},
    ssl: Optional[ssl.SSLContext] = None,
) -> None:
    """
    Download from `url` to an httpfile-format file.

    This module's docstring describes the file format.

    Raise HttpError if download fails.
    """
    timeout = aiohttp.ClientTimeout(total=5 * 60, connect=30)

    try:
        async with moduleutils.spooled_data_from_url(
            url, headers, timeout, ssl=ssl
        ) as (bytesio, headers, charset):
            # This shouldn't be a context manager. Oh well. Ignore the fact
            # that bytesio is backed by a file. It's safe to read the file
            # after we exit the context and the file is deleted.
            pass
    except asyncio.TimeoutError:
        output_path.write_bytes(b"")  # truncate file
        raise HttpError.Timeout
    except aiohttp.InvalidURL:
        raise HttpError.InvalidUrl
    except aiohttp.TooManyRedirects:
        raise HttpError.TooManyRedirects
    except aiohttp.ClientResponseError as err:
        raise HttpError.ClientResponseError from err
    except aiohttp.ClientError as err:
        raise HttpError.ClientError from err

    # The following shouldn't ever error.
    with output_path.open("wb") as f:
        write(f, url, headers, bytesio)


@contextlib.contextmanager
def read(httpfile_path: Path) -> ContextManager[Tuple[Path, str]]:
    r"""
    Yield `(body: Path, url: str, headers: str)` by parsing `httpfile_path`.

    The yielded `body` contains the downloaded HTTP body. The body is decoded
    according to the HTTP server's `Content-Encoding` and `Transfer-Encoding`.

    The yielded `str` contains HTTP-encoded headers. They are separated by \r\n
    and the final line ends with \r\n. Their `Content-Encoding`,
    `Transfer-Encoding` and `Content-Length` headers are _not_ prefixed with
    `Cjw-Original-`. Do not use these headers to validate `body`, because
    `body` is already decoded.
    """
    with tempfile_context(prefix="body-") as body_path:
        with httpfile_path.open("rb") as f, gzip.GzipFile(mode="rb", fileobj=f) as zf:
            # read params (line 1)
            fetch_params_json = zf.readline()
            fetch_params = json.loads(fetch_params_json)
            url = fetch_params["url"]

            # read and skip status (line 2)
            zf.readline()

            # read headers (lines ending in "\r\n" plus one final "\r\n")
            header_lines = []
            while True:
                line = zf.readline().decode("latin1")
                if not line.strip():
                    # "\r\n" on its own line means "end of headers"
                    break
                if line.startswith("Cjw-Original-"):
                    line = line[len("Cjw-Original-") :]
                header_lines.append(line)
            headers = "".join(header_lines)  # ends with last header_line's "\r\n"

            # Read body into tempfile
            with body_path.open("wb") as body_f:
                shutil.copyfileobj(zf, body_f)

        # Yield
        yield body_path, url, headers


def extract_first_header_from_str(headers: str, header: str) -> Optional[str]:
    r"""
    Scan `headers` for a (case-insensitive) `header`; return its value.

    `headers` must be in the format yielded by `read()`.

    >>> headers = "Content-Type: text/plain; charset=utf-8\r\nX-Foo: Bar\nX-Foo: Baz"

    Searches are case-insensitive:
    >>> extract_first_header_from_str(headers, "content-type")
    "text/plain; charset=utf-8"

    If a header is repeated, only the first value is returned:
    >>> extract_first_header_from_str(headers, "x-foo")
    "Bar"

    If a header is missing, return `None`:
    >>> extract_first_header_from_str(headers, "content-length")
    None
    """
    # Assume headers are well-formed: otherwise we wouldn't have written them
    # to the `headers` value we're parsing here.
    key = header.upper()
    for header_line in headers.split("\r\n"):
        if header_line:  # last split result is ""
            header, value = header_line.split(":", 1)
            if header.upper() == key:
                return value.strip()
    return None
