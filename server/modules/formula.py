from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd
from formulas import Parser
from formulas.errors import FormulaError
import re, itertools
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

    code = compile(formula, '<string>', 'eval')

    # Much experimentation went into the form of this loop for good performance.
    # Note we don't use iterrows or any pandas indexing, and construct the values dict ourselves
    for i,row in enumerate(table.values):
        newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))

    return newcol


def eval_excel_one_row(code, table):

    # Generate a list of input table values for each range in the expression
    formula_args = []
    for token, obj in code.inputs.items():
        ranges = obj.ranges
        if len(ranges) != 1:
            return _('Excel range must be a rectangular block of values')  # ...how to get here?
        range = ranges[0]

        # Unpack start/end row/col
        r1 = int(range['r1'])-1
        r2 = int(range['r2'])
        c1 = int(range['n1'])-1
        c2 = int(range['n2'])

        nrows, ncols = table.shape
        if r1<0 or r1>=nrows or c1<0 or c1>=ncols:
            return '#REF!' # expression references non-existent data

        table_part = list(table.iloc[r1:r2,c1:c2].values.flat)
        formula_args.append(table_part)

    # evaluate the formula just once
    return code(*formula_args)


def eval_excel_all_rows(code, table, newcol):
    col_idx = []
    for token, obj in code.inputs.items():
        # If the formula is valid but no object comes back it means the reference is no good
        # Missing row number?
        # with only A-Z. But just in case:
        if obj is None:
            raise _('Bad cell reference %s' % token)

        ranges = obj.ranges
        to_index = []
        for rng in ranges:
            # r1 and r2 refer to which rows are referenced by the range.
            # cr shows up in the range object whenever the reference is to
            # an entire row.
            if (rng['r1'] != '1' and rng['r2'] != '1') and rng['cr'] != '1':
                raise _(
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
            if isinstance(col, list):
                args_to_excel.append([row[idx] for idx in col])
            else:
                args_to_excel.append(row[col])
        newcol[i] = code(*args_to_excel)

    return newcol


def excel_formula(table, formula, all_rows, newcol):
    try:
        # 0 is a list of tokens, 1 is the function builder object
        code = Parser().ast(formula)[1].compile()
    except Exception as e:
        raise  _("Couldn't parse formula: %s" % str(e))

    if all_rows:
        return eval_excel_all_rows(code, table, newcol)
    else:
        newcol[0] = eval_excel_one_row(code, table)
        return newcol


class Formula(ModuleImpl):

    def render(wf_module, table):

        if table is None:
            return None     # no rows to process

        newcol = pd.Series(list(itertools.repeat(None, len(table))))

        syntax = wf_module.get_param_menu_idx('syntax')
        if syntax== 0:
            formula = wf_module.get_param_string('formula_excel').strip()
            if formula=='':
                return table
            all_rows = wf_module.get_param_checkbox('all_rows')
            try:
                newcol = excel_formula(table, formula, all_rows, newcol)
            except Exception as e:
                return str(e)
        else:
            formula = wf_module.get_param_string('formula_python').strip()
            if formula=='':
                return table
            try:
                newcol = python_formula(table, formula, newcol)
            except Exception as e:
                return str(e)

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
