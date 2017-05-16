from .moduleimpl import ModuleImpl
from .utils import *
import pandas as pd

# ---- PythonCode ----

# adds two spaces before every line
def indent_lines(str):
    return '  ' + str.replace('\n', '\n  ');

class PythonCode(ModuleImpl):
    def render(wf_module, table):
        code = wf_module.get_param_string('code')

        # turn the user-supplied text into a function declaration
        code = 'def process(table):\n' + indent_lines(code)

        # this is where we will store the function we define
        locals = {}

        # Catch errors with the code and display to user
        try:
            exec(code, custom_code_globals, locals )

        except Exception as e:
            wf_module.set_error(str(e))
            return None

        if not 'process' in locals:
            wf_module.set_error('Problem defining function')
            return None

        out_table = locals['process'](table)
        return out_table

