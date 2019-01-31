import aiohttp
import asyncio
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server.modules import utils
from .utils import parse_bytesio, turn_header_into_first_row


ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ),
    '.csv': 'text/csv',
    '.tsv': 'text/tab-separated-values',
    '.json': 'application/json',
}


AllowedMimeTypes = list(ExtensionMimeTypes.values())


NonstandardMimeTypes = {
    'application/csv': 'text/csv',
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


class LoadURL(ModuleImpl):
    # Input table ignored.
    @staticmethod
    def render(table, params, *, fetch_result, **kwargs):
        if not fetch_result:
            return ProcessResult(table)  # no-op

        table = fetch_result.dataframe
        error = fetch_result.error

        has_header: bool = params['has_header']
        if not has_header:
            table = turn_header_into_first_row(table)

        return ProcessResult(table, error)

    # Load a CSV from file when fetch pressed
    @staticmethod
    async def fetch(params, **kwargs):
        url: str = params['url'].strip()

        mimetypes = ','.join(AllowedMimeTypes)
        headers = {'Accept': mimetypes}
        timeout = aiohttp.ClientTimeout(total=5*60, connect=30)

        try:
            async with utils.spooled_data_from_url(
                url, headers, timeout
            ) as (bytes_io, headers, charset):
                content_type = headers.get('Content-Type', '') \
                        .split(';')[0] \
                        .strip()
                mime_type = guess_mime_type_or_none(content_type, url)

                if mime_type:
                    result = parse_bytesio(bytes_io, mime_type, charset)
                    result.truncate_in_place_if_too_big()
                    result.sanitize_in_place()
                    return result
                else:
                    return ProcessResult(error=(
                        f'Error fetching {url}: '
                        f'unknown content type {content_type}'
                    ))
        except asyncio.TimeoutError:
            return ProcessResult(error=f'Timeout fetching {url}')
        except aiohttp.InvalidURL:
            return ProcessResult(error=f'Invalid URL')
        except aiohttp.ClientResponseError as err:
            return ProcessResult(error=('Error from server: %d %s'
                                        % (err.status, err.message)))
        except aiohttp.ClientError as err:
            return ProcessResult(error=str(err))
