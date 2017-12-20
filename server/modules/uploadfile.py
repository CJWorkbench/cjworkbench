from .moduleimpl import ModuleImpl
from server.utils import sanitize_dataframe
from pandas.errors import ParserError
from xlrd import XLRDError
from .utils import *

class UploadFile(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        file = wf_module.retrieve_fetched_file()
        if file is None:
            wf_module.set_ready(notify=True)
            return

        if file.name.endswith('.xls') or file.name.endswith('.xlsx') or file.name.endswith('.XLS') or file.name.endswith('.XLSX'):

            try:
                table_aux = pd.read_excel(file)
            except XLRDError as e:
                wf_module.set_error(str(e))
                return None

            sanitize_dataframe(table_aux)
            wf_module.set_ready(notify=True)
            return table_aux

        elif file.name.endswith('.csv') or file.name.endswith('.CSV'):
            try:
                table_aux = pd.read_csv(file)
            except ParserError as e:
                wf_module.set_error(str(e))
                return None

            sanitize_dataframe(table_aux)
            wf_module.set_ready(notify=True)
            return table_aux

        else:
            wf_module.set_error('Unknown file type.', notify=True)
            return None
