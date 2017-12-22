from .moduleimpl import ModuleImpl
from server.utils import sanitize_dataframe
from pandas.errors import ParserError
from xlrd import XLRDError
from .utils import *
import os

class UploadFile(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        so = wf_module.retrieve_fetched_file_so()
        if so is None:
            wf_module.set_ready(notify=True)
            return

        filename, file_ext= os.path.splitext(so.name)  # original upload name, not the name of our cache file
        file_ext = file_ext.lower()

        if file_ext=='.xlsx' or file_ext=='.xls':
            try:
                table_aux = pd.read_excel(so.file)
            except XLRDError as e:
                wf_module.set_error(str(e))
                return None

        elif file_ext=='.csv':
            try:
                table_aux = pd.read_csv(so.file)
            except ParserError as e:
                wf_module.set_error(str(e))
                return None

        else:
            wf_module.set_error('Unknown file type ' + file_ext, notify=True)
            return None

        sanitize_dataframe(table_aux)
        wf_module.set_ready(notify=True)
        return table_aux


