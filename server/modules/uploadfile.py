from .moduleimpl import ModuleImpl
from .utils import *
import io

class UploadFile(ModuleImpl):

    # Input table ignored.
    @staticmethod
    def render(wf_module, table):
        file = wf_module.retrieve_file()
        if file != None:
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                return pd.read_excel(file)
            elif file.name.endswith('.csv'):
                return pd.read_csv(file)
            else:
                wf_module.set_error('Unknown file type.')
                return None
        else:
            return None
        wf_module.set_ready(notify=False)