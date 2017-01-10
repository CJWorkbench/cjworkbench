# Module dispatch table and implementations
import pandas as pd

# ---- Module implementations ---

# input table ignored
def M_LoadCSV(wf_module, table):
    print("M_LoadCSV executing")
    url = wf_module.get_param_string("URL")
    table = pd.Series(['url', url])
    return table

def M_Formula(module, table):
    print("M_Formula executing")
    return table

def M_RawCode(module, table):
    print("M_RawCode executing")
    return table

def M_SimpleChart(module, table):
    print("M_SimpleChart executing")
    return table

module_dispatch = {
    'loadcsv':      M_LoadCSV,
    'formula':      M_Formula,
    'rawcode':      M_RawCode,
    'simplechart':  M_SimpleChart
}
