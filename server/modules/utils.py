from typing import Any, Dict


class PythonFeatureDisabledError(Exception):
    def __init__(self, name):
        super().__init__(self)
        self.name = name
        self.message = f'{name} disabled in Python Code module'


def build_globals_for_eval() -> Dict[str, Any]:
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
