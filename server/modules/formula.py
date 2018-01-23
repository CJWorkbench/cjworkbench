from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd

# ---- Formula ----

class Formula(ModuleImpl):
    def render(wf_module, table):

        if table is None:
            return None     # no rows to process

        formula = wf_module.get_param_string('formula').strip()
        if formula == '':
            return table    # nop if no formula

        colnames = list(table.columns)
        newcol = pd.Series(np.zeros(len(table)))

        # Catch errors with the formula and display to user
        try:
            code = compile(formula, '<string>', 'eval')

            # Much experimentation went into the form of this loop for good performance.
            # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
            for i,row in enumerate(table.values):
                newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))
        except Exception as e:
            return(str(e))

        # if no output column supplied, use result0, result1, etc.
        out_column = wf_module.get_param_string('out_column')
        if out_column == '':
            if 'result' not in colnames:
                out_column='result'
            else:
                n=0
                while 'result' + str(n) in colnames:
                    n+=1
                out_column = 'result' + str(n)
        table[out_column] = newcol

        wf_module.set_ready(notify=False)
        return table
