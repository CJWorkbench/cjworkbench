from .moduleimpl import ModuleImpl
from .utils import *
import sys
import traceback

# ---- PythonCode ----

# adds two spaces before every line
def indent_lines(str):
    return '  ' + str.replace('\n', '\n  ');

def errorstring(line, errstr):
    return errstr + ' at line ' + str(line-1)  # line-1 to remove the def line we added

class PythonCode(ModuleImpl):

    def render(wf_module, table):
        code = wf_module.get_param_raw('code', 'custom')

        # empty code, NOP
        code = code.strip()
        if code == '':
            return table

        # turn the user-supplied text into a function declaration
        code = 'def process(table):\n' + indent_lines(code)

        # this is where we will store the function we define
        locals = {}

        # Catch errors with the code and display to user
        try:
            exec(code, custom_code_globals, locals )
            out_table = locals['process'](table)

        except SyntaxError as err:
            wf_module.set_error(errorstring(err.lineno, str(err)))
            return None
        except Exception as err:
            cl, exc, tb = sys.exc_info()
            lineno = traceback.extract_tb(tb)[1][1]
            wf_module.set_error(errorstring(lineno, str(err)))
            return None

        return out_table
