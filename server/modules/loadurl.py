import aiohttp
import asyncio
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server.modules import utils
from .utils import parse_bytesio, turn_header_into_first_row

# ---- LoadURL ----


_ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ),
    '.csv': 'text/csv',
    '.tsv': 'text/tab-separated-values',
    '.json': 'application/json',
}


def guess_mime_type_or_none(content_type: str, url: str) -> str:
    """Infer MIME type from Content-Type header or URL, or return None."""
    for mime_type in _ExtensionMimeTypes.values():
        if content_type.startswith(mime_type):
            return mime_type

    for extension, mime_type in _ExtensionMimeTypes.items():
        if extension in url:
            return mime_type

    return None


class LoadURL(ModuleImpl):
    # Input table ignored.
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return ProcessResult(table)  # no-op

        table = fetch_result.dataframe
        error = fetch_result.error

        if not params.get_param_checkbox('has_header'):
            table = turn_header_into_first_row(table)

        return ProcessResult(table, error)

    # Load a CSV from file when fetch pressed
    @staticmethod
    async def fetch(wf_module):
        params = wf_module.get_params()
        url = params.get_param_string('url').strip()

        mimetypes = ','.join(_ExtensionMimeTypes.values())
        headers = {'Accept': mimetypes}
        timeout = aiohttp.ClientTimeout(total=5*60, connect=30)

        try:
            async with utils.spooled_data_from_url(
                url, headers, timeout
            ) as (bytes_io, headers, charset):
                content_type = headers.get('content-type', '') \
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
