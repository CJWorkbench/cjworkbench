import asyncio
from cjworkbench.types import ProcessResult
from server import minio
from .utils import parse_bytesio, turn_header_into_first_row


_ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx':
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',
    '.tsv': 'text/tab-separated-values',
    '.json': 'application/json',
    '.txt': 'text/plain'
}


# --- Parse UploadedFile ---
# When files come in, they are stored in temporary UploadedFile objects
# This code parses the file into a table, and stores as a StoredObject

def _load_uploaded_file(bucket, key, mime_type) -> ProcessResult:
    """BLOCKING: download from S3 and load with parse_bytesio()."""
    try:
        # Download, don't stream: it's faster because it's concurrent
        with minio.temporarily_download(bucket, key) as path:
            with path.open('rb') as f:
                result = parse_bytesio(f, mime_type, None)

    except minio.error.ClientError as err:
        return ProcessResult(error=str(err))

    result.truncate_in_place_if_too_big()
    return result


# Read an UploadedFile, parse it, store it as the WfModule's "fetched table"
# Public entrypoint, called by the view
async def parse_uploaded_file(uploaded_file) -> ProcessResult:
    """
    Convert an UploadedFile to a ProcessResult.

    TODO make this synchronous, and move it somewhere sensible. See comments
    surrounding "upload_DELETEME".

    This is async because it can take a long time: the processing happens in a
    background thread.
    """
    ext = '.' + uploaded_file.name.split('.')[-1]
    mime_type = _ExtensionMimeTypes.get(ext, None)
    loop = asyncio.get_event_loop()
    if mime_type:
        result = await loop.run_in_executor(None, _load_uploaded_file,
                                            uploaded_file.bucket,
                                            uploaded_file.key, mime_type)
    else:
        return ProcessResult(error=(
            f'Error parsing {uploaded_file.name}: unknown content type'
        ))

    # don't delete UploadedFile, so that we can reparse later or allow higher
    # row limit or download original, etc.
    return result


def render(table, params, *, fetch_result):
    if not fetch_result:
        return table  # user hasn't uploaded yet

    if fetch_result.status == 'error':
        return fetch_result.error

    table = fetch_result.dataframe
    has_header: bool = params['has_header']
    if not has_header:
        table = turn_header_into_first_row(table)

    if fetch_result.error:
        return (table, fetch_result.error)
    else:
        return table
