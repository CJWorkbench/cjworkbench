from io import BufferedReader
from server.minio import open_for_read, ResponseError
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import parse_bytesio, turn_header_into_first_row
from server.utils import TempfileBackedReader


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

# Read an UploadedFile, parse it, store it as the WfModule's "fetched table"
# Public entrypoint, called by the view
def upload_to_table(wf_module, uploaded_file):
    ext = '.' + uploaded_file.name.split('.')[-1]
    mime_type = _ExtensionMimeTypes.get(ext, None)
    if mime_type:
        try:
            with open_for_read(uploaded_file.bucket, uploaded_file.key) as s3:
                with TempfileBackedReader(s3) as tempio:
                    with BufferedReader(tempio) as bufio:
                        result = parse_bytesio(bufio, mime_type, None)
        except ResponseError as err:
            result = ProcessResult(error=str(err))
    else:
        result = ProcessResult(error=(
            f'Error parsing {uploaded_file.file.name}: '
            'unknown content type'
        ))

    if result.error:
        # delete uploaded file, we probably can't ever use it
        uploaded_file.delete()

    result.truncate_in_place_if_too_big()
    result.sanitize_in_place()

    ModuleImpl.commit_result(wf_module, result, stored_object_json=[
        {'uuid': uploaded_file.uuid, 'name': uploaded_file.name}
    ])

    # don't delete UploadedFile, so that we can reparse later or allow higher
    # row limit or download original, etc.
    return


class UploadFile(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        # Must perform header operation here in the event the header checkbox
        # state changes
        has_header = wf_module.get_param_checkbox('has_header')
        if not has_header:
            return ProcessResult(
                turn_header_into_first_row(wf_module.retrieve_fetched_table()),
                wf_module.error_msg
            )
        else:
            return ProcessResult(
                wf_module.retrieve_fetched_table(),
                wf_module.error_msg
            )
