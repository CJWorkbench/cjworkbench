from .moduleimpl import ModuleImpl
import pandas as pd
from pandas.parser import CParserError
import io


# ---- PasteCSV ----
# Lets the user paste in text which it interprets as a exce
class PasteCSV(ModuleImpl):

    def render(wf_module, table):
        tablestr = wf_module.get_param_string("csv")

        has_header_row = wf_module.get_param_checkbox("has_header_row")

        if has_header_row:
            header_row = 0
        else:
            header_row = None

        if (len(tablestr)==0):
            wf_module.set_error('Please enter a CSV')
            return None
        try:
            table = pd.read_csv(io.StringIO(tablestr), header=header_row, 
                    delimiter=' *, *', engine='python')
        except CParserError as e:
            wf_module.set_error(str(e))
            return None

        wf_module.set_ready(notify=False)
        return table
