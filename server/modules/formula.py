from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd
from formulas import Parser
import re

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

        newcol = pd.Series(np.zeros(len(table)))

        syntax = wf_module.get_param_menu_idx('syntax')

        if syntax == 0: # Python
            colnames = [x.replace(" ", "_") for x in table.columns]  # spaces to underscores in column names

            # Catch errors with the formula and display to user
            try:
                code = compile(formula, '<string>', 'eval')

                # Much experimentation went into the form of this loop for good performance.
                # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
                for i,row in enumerate(table.values):
                    newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))
            except Exception as e:
                return(str(e))

        if syntax == 1: # Excel
            try:
                code = Parser().ast(formula)[1].compile()
            except Exception as e:
                return "Couldn't parse formula: %s" % str(e)

            col_idx = []

            for token, obj in code.inputs.items():
                # If the formula is valid but no object comes
                # back it means we should have an uppercase string
                # with only A-Z. But just in case:
                if obj is None:
                    to_index = re.sub(r"[0-9]+", '', token)
                    to_index = [letter_ref_to_number(to_index)]
                else:
                    ranges = obj.ranges
                    to_index = []
                    for rng in ranges:
                        col_first = rng['n1']
                        col_last = rng['n2']
                        if col_first != col_last:
                            to_index.append([n for n in range((col_first-1), col_last)])
                        else:
                            to_index.append(col_first - 1)
                if len(to_index) == 1:
                    col_idx.append(to_index[0])
                else:
                    col_idx.append(to_index)

            for i, row in enumerate(table.values):
                args_to_excel = []
                for col in col_idx:
                    if isinstance(col, list):
                        args_to_excel.append([row[idx] for idx in col])
                    else:
                        args_to_excel.append(row[col])
                try:
                    newcol[i] = code(*args_to_excel)
                except Exception as e:
                    return str(e)

        # if no output column supplied, use result0, result1, etc.
        out_column = wf_module.get_param_string('out_column')
        if out_column == '':
            if 'result' not in colnames:
                out_column = 'result'
            else:
                n = 0
                while 'result' + str(n) in colnames:
                    n += 1
                out_column = 'result' + str(n)
        table[out_column] = newcol








        wf_module.set_ready(notify=False)
        return table
