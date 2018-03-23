from django.conf import settings
from server.models.UploadedFile import UploadedFile
from server.models.StoredObject import StoredObject
from server.utils import sanitize_dataframe,truncate_table_if_too_big
from server.models import ChangeDataVersionCommand, StoredObject
from django.utils.translation import gettext as _
from .moduleimpl import ModuleImpl
import pandas as pd
from pandas.errors import ParserError
from xlrd import XLRDError
import os
import json

# --- Parse UploadedFile ---
# When files come in, they are stored in temporary UploadedFile objects
# This code parses the file into a table, and stores as a "fetched" StoredObject

# Read an UploadedFile, parse it, store it as the WfModule's "fetched table"
# Public entrypoint, called by the view
def upload_to_table(wf_module, uploaded_file):
    table = __parse_uploaded_file(uploaded_file)

    if isinstance(table, str):
        return table  # return error message if we could not parse

    # Cut this file down to size to prevent reading in the hugest data on every render
    nrows = len(table)
    truncated = truncate_table_if_too_big(table)

    sanitize_dataframe(table)

    # Save the new output, creating and switching to a new data version
    version_added = wf_module.store_fetched_table(table)

    # set new StoredObject metadata to the json response the client expects, containing filename and uuid
    # (see views.UploadedFile.get)
    new_so = StoredObject.objects.get(wf_module=wf_module, stored_at=version_added)
    result = [{'uuid': uploaded_file.uuid, 'name': uploaded_file.name}]
    new_so.metadata = json.dumps(result)
    new_so.save()

    ChangeDataVersionCommand.create(wf_module, version_added)  # also notifies client

    # if we made it this far we have stored the table corresponding to the file, so we can delete the file
    uploaded_file.delete()

    if not truncated:
        # start of file upload set module busy status on client side; undo this. Need a better notification system.
        wf_module.set_ready(notify=True)
    else:
        error = _('File has %d rows, truncated to %d' % (nrows, settings.MAX_ROWS_PER_TABLE))
        wf_module.set_error(error, notify=True)


# private
def __parse_uploaded_file(ufile):
    filename, file_ext = os.path.splitext(ufile.name)  # original upload name, not the name of our cache file
    file_ext = file_ext.lower()

    if file_ext == '.xlsx' or file_ext == '.xls':
        try:
            table = pd.read_excel(ufile.file)
        except XLRDError as e:
            return (str(e))

    elif file_ext == '.csv':
        try:
            table = pd.read_csv(ufile.file)
        except ParserError as e:
            return (str(e))

    else:
        return (_('Unknown file type %s' % file_ext))

    return table


# --- Upload module ---
# Nothing to it, much like LoadURL

class UploadFile(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        return wf_module.retrieve_fetched_table()



