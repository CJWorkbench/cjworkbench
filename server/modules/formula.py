import itertools
from formulas import Parser
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
from schedula import DispatcherError
from cjwkernel.pandas.moduleutils import autocast_series_dtype, build_globals_for_eval


def sanitize_series(series: pd.Series) -> pd.Series:
    """
    Enforce type rules on input pandas `Series.values`.

    The return value is anything that can be passed to the `pandas.Series()`
    constructor.

    Specific fixes:

    * Make sure categories have no excess values.
    * Convert numeric categories to 
    * Convert unsupported dtypes to string.
    * Reindex so row numbers are contiguous.
    """
    series.reset_index(drop=True, inplace=True)
    if hasattr(series, "cat"):
        series.cat.remove_unused_categories(inplace=True)

        categories = series.cat.categories
        if pd.api.types.is_numeric_dtype(categories.values):
            # Un-categorize: make array of int/float
            return pd.to_numeric(series)
        elif (
            categories.dtype != object
            or pd.api.types.infer_dtype(categories.values, skipna=True) != "string"
        ):
            # Map from non-Strings to Strings
            #
            # 1. map the _codes_ to unique _codes_
            mapping = pd.Categorical(categories.astype(str))
            values = pd.Categorical(series.cat.codes[mapping.codes])
            # 2. give them names
            values.rename_categories(mapping.categories, inplace=True)
            series = pd.Series(values)

        return series
    elif is_numeric_dtype(series.dtype):
        return series
    elif is_datetime64_dtype(series.dtype):
        return series
    else:
        # Force it to be a str column: every object is either str or np.nan
        ret = series.astype(str)
        ret[pd.isna(series)] = np.nan
        return ret


def python_formula(table, formula):
    # spaces to underscores in column names
    colnames = [x.replace(" ", "_") for x in table.columns]

    code = compile(formula, "<string>", "eval")
    custom_code_globals = build_globals_for_eval()

    # Much experimentation went into the form of this loop for good
    # performance.
    # Note we don't use iterrows or any pandas indexing, and construct the
    # values dict ourselves
    newcol = pd.Series(list(itertools.repeat(None, len(table))))
    for i, row in enumerate(table.values):
        newcol[i] = eval(code, custom_code_globals, dict(zip(colnames, row)))

    newcol = autocast_series_dtype(sanitize_series(newcol))

    return newcol


def flatten_single_element_lists(x):
    """Return `x[0]` if `x` is a list, otherwise `x`."""
    if isinstance(x, list) and len(x) == 1:
        return x[0]
    else:
        return x


def eval_excel(code, args):
    """
    Return result of running Excel code with args.

    Raise ValueError if a function is unimplemented.
    """
    try:
        ret = code(*args)
    except DispatcherError as err:
        raise ValueError(
            ", ".join(str(arg) for arg in err.args[1:-1]) + ": " + str(err.args[-1])
        )
    if isinstance(ret, np.ndarray):
        return ret.item()
    else:
        return ret


def eval_excel_one_row(code, table):

    # Generate a list of input table values for each range in the expression
    formula_args = []
    for token, obj in code.inputs.items():
        if obj is None:
            raise ValueError("Invalid cell range: %s" % token)
        ranges = obj.ranges
        if len(ranges) != 1:
            # ...not sure what input would get us here
            raise ValueError("Excel range must be a rectangular block of values")
        range = ranges[0]

        # Unpack start/end row/col
        r1 = int(range["r1"]) - 1
        r2 = int(range["r2"])
        c1 = int(range["n1"]) - 1
        c2 = int(range["n2"])

        nrows, ncols = table.shape
        if r1 < 0 or r1 >= nrows or c1 < 0 or c1 >= ncols:
            # expression references non-existent data
            return "#REF!"

        # retval of code() is OperatorArray:
        # https://github.com/vinci1it2000/formulas/issues/12
        table_part = list(table.iloc[r1:r2, c1:c2].values.flat)
        formula_args.append(flatten_single_element_lists(table_part))

    # evaluate the formula just once
    # raises ValueError if function isn't implemented
    return eval_excel(code, formula_args)


def eval_excel_all_rows(code, table):
    col_idx = []
    for token, obj in code.inputs.items():
        # If the formula is valid but no object comes back it means the
        # reference is no good
        # Missing row number?
        # with only A-Z. But just in case:
        if obj is None:
            raise ValueError(f"Bad cell reference {token}")

        ranges = obj.ranges
        for rng in ranges:
            # r1 and r2 refer to which rows are referenced by the range.
            if rng["r1"] != "1" or rng["r2"] != "1":
                raise ValueError(
                    "Excel formulas can only reference "
                    "the first row when applied to all rows"
                )

            col_first = rng["n1"]
            col_last = rng["n2"]

            col_idx.append(list(range(col_first - 1, col_last)))

    newcol = []
    for row in table.values:
        args_to_excel = [
            flatten_single_element_lists([row[idx] for idx in col]) for col in col_idx
        ]
        # raises ValueError if function isn't implemented
        newcol.append(eval_excel(code, args_to_excel))

    return pd.Series(newcol)


def excel_formula(table, formula, all_rows):
    try:
        # 0 is a list of tokens, 1 is the function builder object
        code = Parser().ast(formula)[1].compile()
    except Exception as e:
        raise ValueError(f"Couldn't parse formula: {str(e)}")

    if all_rows:
        newcol = eval_excel_all_rows(code, table)
        newcol = autocast_series_dtype(sanitize_series(newcol))
    else:
        # the whole column is blank except first row
        value = eval_excel_one_row(code, table)
        newcol = pd.Series([value] + [None] * (len(table) - 1))

    return newcol


def _get_output_column(table, out_column: str) -> str:
    # if no output column supplied, use result0, result1, etc.
    if not out_column:
        out_column = "result"

    # make sure the colname is unique
    if out_column in table.columns:
        n = 0
        while f"{out_column}{n}" in table.columns:
            n += 1
    else:
        n = ""
    return f"{out_column}{n}"


def render(table, params, **kwargs):
    if table is None:
        return None  # no rows to process

    if params["syntax"] == "excel":
        formula: str = params["formula_excel"].strip()
        if not formula:
            return table
        all_rows: bool = params["all_rows"]
        try:
            newcol = excel_formula(table, formula, all_rows)
        except Exception as e:
            return str(e)
    else:
        formula: str = params["formula_python"].strip()
        if not formula:
            return table
        try:
            newcol = python_formula(table, formula)
        except Exception as e:
            return str(e)

    out_column = _get_output_column(table, params["out_column"])
    table[out_column] = newcol

    return table


def _migrate_params_v0_to_v1(params):
    """
    v0: syntax is int, 0 means excel, 1 means python

    v1: syntax is 'excel' or 'python'
    """
    return {**params, "syntax": ["excel", "python"][params["syntax"]]}


def migrate_params(params):
    if isinstance(params["syntax"], int):
        params = _migrate_params_v0_to_v1(params)
    return params
