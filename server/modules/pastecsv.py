from .moduleimpl import ModuleImpl
from .types import ProcessResult
import pandas as pd
from pandas.io.common import EmptyDataError, ParserError
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

        # Guess at format by counting commas and tabs
        n_commas = tablestr.count(',')
        n_tabs = tablestr.count('\t')
        if n_commas > n_tabs:
            sep = ','
        else:
            sep = '\t'

        try:
            table = pd.read_table(io.StringIO(tablestr), header=header_row,
                                  skipinitialspace=True, sep=sep)
        except EmptyDataError:
            return ProcessResult(pd.DataFrame())
        except ParserError as err:
            return ProcessResult(error=str(err))

        return ProcessResult(table)
