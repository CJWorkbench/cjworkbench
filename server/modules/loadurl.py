import aiohttp
import asyncio
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.pandas import moduleutils
from cjwkernel.pandas.parse_util import parse_bytesio


ExtensionMimeTypes = {
    ".xls": "application/vnd.ms-excel",
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
}


AllowedMimeTypes = list(ExtensionMimeTypes.values())


NonstandardMimeTypes = {"application/csv": "text/csv"}


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


def render(table, params, *, fetch_result, **kwargs):
    if not fetch_result:
        return ProcessResult(table)  # no-op

    table = fetch_result.dataframe
    error = fetch_result.error

    has_header: bool = params["has_header"]
    if not has_header:
        table = moduleutils.turn_header_into_first_row(table)

    return ProcessResult(table, error)


async def fetch(params, **kwargs):
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
            content_type = headers.get("Content-Type", "").split(";")[0].strip()
            mime_type = guess_mime_type_or_none(content_type, url)

            if mime_type:
                # FIXME has_header=True always, because of a stupid decision
                # ages ago that we can't fix because everything we've stored
                # was stored with has_header=True (which is lossy).
                #
                # In https://www.pivotaltracker.com/story/show/166712967 we'll
                # store the input file instead of parsed file; then we'll be
                # able to parse correctly moving forward.
                #
                # FIXME move this to render(). In the meantime, we need to
                # run_in_executor() so we continue to send AMQP heartbeats and
                # handle other HTTP connections, even when parsing a big file.
                return await asyncio.get_event_loop().run_in_executor(
                    None, parse_bytesio, bytesio, charset, mime_type, True  # has_header
                )
            else:
                return ProcessResult(
                    error=(
                        f"Error fetching {url}: " f"unknown content type {content_type}"
                    )
                )
    except asyncio.TimeoutError:
        return ProcessResult(error=f"Timeout fetching {url}")
    except aiohttp.InvalidURL:
        return ProcessResult(error=f"Invalid URL")
    except aiohttp.ClientResponseError as err:
        return ProcessResult(
            error=("Error from server: %d %s" % (err.status, err.message))
        )
    except aiohttp.ClientError as err:
        return ProcessResult(error=str(err))
