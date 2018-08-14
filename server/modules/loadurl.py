import io
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import requests
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import parse_bytesio

# ---- LoadURL ----


_ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
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
    def render(wf_module, table):
        return ProcessResult(wf_module.retrieve_fetched_table(),
                             wf_module.error_msg)

    # Load a CSV from file when fetch pressed
    @staticmethod
    def event(wf_module, **kwargs):
        url = wf_module.get_param_string('url').strip()

        validate = URLValidator()
        try:
            validate(url)
        except ValidationError:
            return ModuleImpl.commit_result(wf_module,
                                            ProcessResult(error='Invalid URL'))

        # fetching could take a while so notify clients/users we're working
        wf_module.set_busy()

        mimetypes = ','.join(_ExtensionMimeTypes.values())

        try:
            response = requests.get(url, headers={'Accept': mimetypes})
            if response.status_code == requests.codes.ok:
                # get content type
                content_type = response.headers.get('content-type', '') \
                        .split(';')[0] \
                        .strip()
                mime_type = guess_mime_type_or_none(content_type, url)

                if mime_type:
                    result = parse_bytesio(io.BytesIO(response.content),
                                           mime_type, response.encoding)
                else:
                    result = ProcessResult(error=(
                        f'Error fetching {url}: '
                        f'unknown content type {content_type}'
                    ))
            else:
                result = ProcessResult(
                    error=f'Error {response.status_code} fetching url'
                )
        except requests.exceptions.RequestException as err:
            result = ProcessResult(error=str(err))

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()

        ModuleImpl.commit_result(wf_module, result)
