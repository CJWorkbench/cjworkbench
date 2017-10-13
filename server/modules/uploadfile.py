from .moduleimpl import ModuleImpl
from .utils import *

class UploadFile(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        file = wf_module.retrieve_file()
        if file != None:
            if file.name.endswith('.xls') or file.name.endswith('.xlsx') or file.name.endswith('.XLS') or file.name.endswith('.XLSX'):
                return pd.read_excel(file)
            elif file.name.endswith('.csv') or file.name.endswith('.CSV'):
                return pd.read_csv(file)
            else:
                wf_module.set_error('Unknown file type.')
                return None
        else:
            return None
        wf_module.set_ready(notify=False)