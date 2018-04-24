from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd
from formulas import Parser
from formulas.errors import FormulaError
import re
from django.utils.translation import gettext as _

# ---- Formula ----

def letter_ref_to_number(letter_ref):
    if re.search(r"[^a-zA-Z]+", letter_ref):
        raise FormulaError(_("%s is not a valid reference" % letter_ref))

    return_number = 0

    for idx, letter in enumerate(reversed(letter_ref)):
        return_number += (ord(letter.upper()) - 64) * (26**idx)

    return return_number - 1  # 0-indexed


def python_formula(table, formula, newcol):
    colnames = [x.replace(" ", "_") for x in table.columns]  # spaces to underscores in column names

    # Catch errors with the formula and display to user
    try:
        code = compile(formula, '<string>', 'eval')

        # Much experimentation went into the form of this loop for good performance.
        # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
        for i,row in enumerate(table.values):
            newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))
    except Exception as e:
        return str(e)

    return newcol


def excel_formula(table, formula, newcol):
    try:
        # 0 is a list of tokens, 1 is the function builder object
        code = Parser().ast(formula)[1].compile()
    except Exception as e:
        return _("Couldn't parse formula: %s" % str(e))

    col_idx = []

    for token, obj in code.inputs.items():
        # If the formula is valid but no object comes
        # back it means we should have an uppercase string
        # with only A-Z. But just in case:
        if obj is None:
            try:
                to_index = [letter_ref_to_number(token)]
            except FormulaError as e:
                # args[1] is the 1st argument to the FormulaError constructor, which is the
                # thing the parser choked on
                return e.msg % (e.args[1] or '')
        else:
            ranges = obj.ranges
            to_index = []
            for rng in ranges:
                # r1 and r2 refer to which rows are referenced by the range.
                # cr shows up in the range object whenever the reference is to
                # an entire row.
                if (rng['r1'] != '1' and rng['r2'] != '1') and rng['cr'] != '1':
                    return _(
                        "Currently only references to entire columns or the first row of a column are supported for excel formulas")

                col_first = rng['n1']
                col_last = rng['n2']

                if col_first != col_last:
                    to_index.append([n for n in range((col_first - 1), col_last)])
                else:
                    to_index.append(col_first - 1)
        if len(to_index) == 1:
            col_idx.append(to_index[0])
        else:
            col_idx.append(to_index)

    for i, row in enumerate(table.values):
        args_to_excel = []
        for col in col_idx:
            try:
                if isinstance(col, list):
                    args_to_excel.append([row[idx] for idx in col])
                else:
                    args_to_excel.append(row[col])
            except IndexError as e:
                return str(e)
        try:
            newcol[i] = code(*args_to_excel)
        except Exception as e:
            return str(e)

    return newcol


class Formula(ModuleImpl):

    def render(wf_module, table):

        if table is None:
            return None     # no rows to process

        syntax = wf_module.get_param_menu_idx('syntax')
        if syntax== 0:
            formula = wf_module.get_param_string('formula_excel').strip()
        else:
            formula = wf_module.get_param_string('formula_python').strip()
        if formula == '':
            return table    # nop if no formula

        newcol = pd.Series(np.zeros(len(table)), dtype=np.dtype(object))

        if syntax == 0:  # Excel
            newcol = excel_formula(table, formula, newcol)

        if syntax == 1:  # Python
            newcol = python_formula(table, formula, newcol)

        if isinstance(newcol, str):
            return newcol

        # if no output column supplied, use result0, result1, etc.
        out_column = wf_module.get_param_string('out_column')
        if out_column == '':
            if 'result' not in table.columns:
                out_column = 'result'
            else:
                n = 0
                while 'result' + str(n) in colnames:
                    n += 1
                out_column = 'result' + str(n)
        table[out_column] = newcol

        wf_module.set_ready(notify=False)
        return table
