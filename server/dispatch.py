# Module dispatch table and implementations
import pandas as pd

# ---- Module implementations ---

# input table ignored
def mimpl_load_csv(wfmodule, table):
    url = wfmodule.get_param_string("URL")
    table = pd.Series(['url', url])
    return table

def mimpl_formula(module, table):
    return table

def mimpl_raw_code(module, table):
    return table

def mimpl_chart(module, table):
    return table

def mimpl_test_data_N(wfmodule, table):
    table = pd.DataFrame(columns=['N', 'N squared'])
    rows = wfmodule.get_param_number('Rows')
    for i in range(int(rows)):
        table.loc[i] = [i+1, (i+1)*(i+1)]
    return table

# ---- Test Support ----
# NOP -- do nothing
def mimpl_NOP(module, table):
    print("NOP executing")
    return table

# Generate test data

test_data_table = pd.DataFrame( {   'Class' : ['math', 'english', 'history'],
                                    'M'     : [ '10', '5', '11' ],
                                    'F'     : [ '12', '7', '13'] } )
def mimpl_test_data(module, table):
    return test_data_table

# Dobule the M column
def mimpl_test_double_M_col(module, table):
    return pd.DataFrame(table['Class'], table['M']*2, table['F'])


module_dispatch = {
    'loadcsv':      mimpl_load_csv,
    'formula':      mimpl_formula,
    'rawcode':      mimpl_raw_code,
    'simplechart':  mimpl_chart,
    'testdataN':    mimpl_test_data_N,

    # For testing
    'NOP':          mimpl_NOP,
    'testdata':     mimpl_test_data,
    'double_M_col': mimpl_test_double_M_col
}
