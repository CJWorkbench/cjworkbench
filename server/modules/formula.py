from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd
from formulas import Parser

# ---- Formula ----

def letter_ref_to_number(letter_ref):
    return_number = 0

    for idx, letter in enumerate(reversed(letter_ref)):
        return_number += (ord(letter.upper()) - 64) * (26**idx)

    return return_number - 1  # 0-indexed

class Formula(ModuleImpl):

    def render(wf_module, table):

        if table is None:
            return None     # no rows to process

        formula = wf_module.get_param_string('formula').strip()
        if formula == '':
            return table    # nop if no formula

        syntax = wf_module.get_param_menu_idx('syntax')

        if syntax == 0: # Python
            colnames = [x.replace(" ", "_") for x in table.columns]  # spaces to underscores in column names
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

        if syntax == 1:
            try:
                code = Parser().ast(formula)[1].compile()
            except Exception as e:
                return "Couldn't parse formula: %s" % str(e)
            
            import pdb; pdb.set_trace()


        wf_module.set_ready(notify=False)
        return table
