from inspect import signature
from .utils import PythonFeatureDisabledError, build_globals_for_eval
from .moduleimpl import ModuleImpl
import sys
import traceback


# ---- PythonCode ----
def errorstring(line, errstr):
    # line-1 to remove the def line we added
    return f'Line {line}: {errstr}'


class PythonCode(ModuleImpl):
    def render(wf_module, table):
        code = wf_module.get_param_raw('code', 'custom')

        # empty code, NOP
        code = code.strip()
        if code == '':
            return table

        # this is where we will store the function we define
        inner_locals = {}

        # Catch errors with the code and display to user
        try:
            # New globals each run
            custom_code_globals = build_globals_for_eval()
            exec(code, custom_code_globals, inner_locals)

            if 'process' not in inner_locals:
                return 'You must define a "process" function'

            process = inner_locals['process']

            sig = signature(process)
            if len(sig.parameters) != 1:
                return (
                    'Your "process" function must '
                    'accept exactly one argument'
                )

            out_table = process(table)

        except SyntaxError as err:
            return errorstring(err.lineno, str(err))
        except PythonFeatureDisabledError as err:
            cl, exc, tb = sys.exc_info()
            lineno = traceback.extract_tb(tb)[1][1]
            return errorstring(lineno, err.message)
        except Exception as err:
            cl, exc, tb = sys.exc_info()
            lineno = traceback.extract_tb(tb)[1][1]
            return errorstring(lineno, f'{type(err).__name__}: {str(err)}')

        return out_table
