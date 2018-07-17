from django.conf import settings
from server.models.StoredObject import StoredObject
from server.models import ChangeDataVersionCommand
from django.utils.translation import gettext as _
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from .utils import parse_bytesio
import pandas as pd
import os
import json


_ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',
    '.tsv': 'text/tab-separated-values',
    '.json': 'application/json',
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
        uploaded_file.file.open()  # Django FileField weirdness
        bytesio = uploaded_file.file
        try:
            result = parse_bytesio(bytesio, mime_type, None)
        except:
            uploaded_file.file.close()
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
        return ProcessResult(wf_module.retrieve_fetched_table())
