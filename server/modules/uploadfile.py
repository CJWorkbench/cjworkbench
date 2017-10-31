from .moduleimpl import ModuleImpl
from .utils import *

class UploadFile(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        wf_module.set_busy(notify=True)
        file = wf_module.retrieve_file()
        if file != None:
            if file.name.endswith('.xls') or file.name.endswith('.xlsx') or file.name.endswith('.XLS') or file.name.endswith('.XLSX'):
                table_aux = pd.read_excel(file)
                wf_module.set_ready(notify=True)
                return table_aux
            elif file.name.endswith('.csv') or file.name.endswith('.CSV'):
                table_aux = pd.read_csv(file)
                wf_module.set_ready(notify=True)
                return table_aux
            else:
                wf_module.set_error('Unknown file type.')
                return None
        else:
            wf_module.set_ready(notify=True)
            return None