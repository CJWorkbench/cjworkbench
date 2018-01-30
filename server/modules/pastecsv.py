from .moduleimpl import ModuleImpl
import pandas as pd
from pandas.io.common import CParserError
import io


# ---- PasteCSV ----
# Lets the user paste in text which it interprets as CSV or TSV
class PasteCSV(ModuleImpl):

    def render(wf_module, table):
        tablestr = wf_module.get_param_string("csv")

        has_header_row = wf_module.get_param_checkbox("has_header_row")

        if has_header_row:
            header_row = 0
        else:
            header_row = None

        if (len(tablestr)==0):
            return('Paste data here')

        # Guess at format by counting commas and tabs
        commas = tablestr.count(',')
        tabs = tablestr.count('\t')
        if commas > tabs:
            sep = ','
        else:
            sep = '\t'

        try:
            table = pd.read_table(io.StringIO(tablestr), header=header_row, skipinitialspace=True, sep=sep)
        except CParserError as e:
            return(str(e))

        return table
