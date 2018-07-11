from inspect import signature
from .moduleimpl import ModuleImpl
import sys
import traceback
from typing import Any, Dict


class PythonFeatureDisabledError(Exception):
    def __init__(self, name):
        super().__init__(self)
        self.name = name
        self.message = f'{name} disabled in Python Code module'


def build_globals() -> Dict[str, Any]:
    """Builds a __globals__ for use in custom code.
    """
    # Start with _this_ module's __builtins__
    builtins = dict()
    for key in dir(__builtins__):
        if key.startswith('__'):
            pass

        try:
            builtins[key] = __builtins__[key]
        except KeyError:
            pass

    # Disable "dangerous" builtins.
    #
    # This doesn't increase security: it just helps module authors.
    def disable_func(name):
        def _disabled(*args, **kwargs):
            raise PythonFeatureDisabledError(name)
        return _disabled
    to_disable = [
        '__import__',
        'breakpoint',
        'compile',
        'eval',
        'exec',
        'open',
    ]
    for name in to_disable:
        builtins[name] = disable_func(name)

    # Hard-code modules we provide the user
    import math
    import pandas as pd
    import numpy as np

    return {
        '__builtins__': builtins,
        'math': math,
        'np': np,
        'pd': pd,
    }


custom_code_globals = build_globals()


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
