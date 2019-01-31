import builtins
import importlib
from inspect import signature
import io
import multiprocessing
import os.path
import sys
import traceback
import math
import numpy
import pandas
from server.models import Params
from .types import ProcessResult
from .utils import build_globals_for_eval, PythonFeatureDisabledError


TIMEOUT = 30.0  # seconds


html_path = os.path.join(os.path.dirname(__file__), 'pythoncode.html')


# Disable dangerous builtins. Imported modules may hold references to them;
# let's hope they don't.
def _disable_builtin(name, d=builtins.__dict__):
    """Put a stub method in builtins, so it cannot be called."""
    def _disabled(*args, **kwargs):
        raise RuntimeError(f'builtins.{name} is disabled')
    d[name] = _disabled


def _scrub_globals_for_safety():
    """
    Permanently destroys builtins and sys functions.

    This will run in a subprocess so it can forget about all ids dangerous
    abilities.
    """
    # Pandas and numpy may use these
    sys_keys_to_keep = [
        'flags',
        'implementation',
        'meta_path',
        'modules',
        'path',
        'path_importer_cache',
        'platform',
        'ps1',
        'ps2',
        'version_info',
        'exc_info',
        'getrecursionlimit',
        'getfilesystemencoding',
        '_getframe',
        '_current_frames',
        'dont_write_bytecode',
        # we overwrote these:
        'stdout',
        'stderr',
        '__stdout__',
        '__stderr__',
    ]

    # Delete every `sys` function and variable. Imported modules may hold
    # references to them; let's hope they don't.
    for key in list(sys.__dict__.keys()):
        if key not in sys_keys_to_keep:
            del sys.__dict__[key]

    # We want pandas.read_csv() to be disabled
    _disable_builtin('breakpoint')
    _disable_builtin('open')
    _disable_builtin('eval')

    # Now re-import modules the modules we'll expose
    importlib.invalidate_caches()
    importlib.reload(math)
    importlib.reload(numpy)
    importlib.reload(pandas)

    # The modules may use these builtins during reload and that's okay.
    # Disable them now that reload is finished.
    _disable_builtin('compile')
    _disable_builtin('exec')


def inner_eval(code, table, sender):
    """Within a subprocess, run code's "process(table)" and exit."""
    result = ProcessResult(json={'output': ''})
    output = io.StringIO()

    def sending_return(*, error=None, tb=None):
        result.json['output'] = output.getvalue()

        if error is not None:
            result.error = error

        return sender.send(result)

    try:
        compiled_code = compile(code, 'user input', 'exec')
    except SyntaxError as err:
        return sending_return(error=f'Line {err.lineno}: {err}')
    except ValueError as err:
        # Apparently this is another thing that compile() can raise
        return sending_return(error=f'User input contains null bytes')

    sys.stdout = sys.stderr = sys.__stdout__ = sys.__stderr__ = output

    code_globals = build_globals_for_eval()

    # Catch errors with the code and display to user
    try:
        exec(compiled_code, code_globals)

        if 'process' not in code_globals:
            return sending_return(error='You must define a "process" function')

        process = code_globals['process']

        sig = signature(process)
        if len(sig.parameters) != 1:
            return sending_return(error=(
                'Your "process" function must accept exactly one argument'
            ))

        out_table = process(table)
    except PythonFeatureDisabledError as err:
        # This is an error _we_ throw. Hide our internals.
        etype, value, tb = sys.exc_info()
        tb = tb.tb_next  # omit _this_ method from the stack trace
        limit = len(traceback.extract_tb(tb)) - 1  # omit _disabled()

        # Now, print the stack trace ... but "rename" the exception so we don't
        # expose its namespace
        # traceback.print_exception(etype, value, tb, limit=limit)
        print('Traceback (most recent call last):')
        traceback.print_tb(tb, limit=limit)
        print(f'{etype.__name__}: {value}')

        return sending_return(error=(
            f'Line {tb.tb_lineno}: {etype.__name__}: {value}'
        ))
    except Exception as err:
        # An error in the code
        etype, value, tb = sys.exc_info()
        tb = tb.tb_next  # omit this method from the stack trace
        traceback.print_exception(etype, value, tb)
        return sending_return(error=(
            f'Line {tb.tb_lineno}: {etype.__name__}: {value}'
        ))

    if isinstance(out_table, code_globals['pd'].DataFrame):
        result.dataframe = out_table
    elif isinstance(out_table, str):
        return sending_return(error=out_table)
    else:
        message = 'process(table) did not return a pd.DataFrame or a str'
        print(message)  # to show it in JSON output
        return sending_return(error=message)

    return sending_return()


def safe_eval_process(code, table, timeout=TIMEOUT):
    """
    Runs `code`'s "process" method in a sandbox and returns a ProcessResult.

    Process stdout, stderr and exception traceback are all stored in
    result.json.output.

    An exception string is also returned in result.error.

    Internally, this method uses multiprocessing to spin up a new Python
    process with restricted execution (a sandbox). The sandbox forbids key
    Python features (such as opening files).
    """
    recver, sender = multiprocessing.Pipe(duplex=False)
    subprocess = multiprocessing.Process(target=inner_eval, name='pythoncode',
                                         daemon=True,
                                         args=[code, table, sender])
    subprocess.start()
    # TODO make this async
    if recver.poll(timeout):
        result = recver.recv()
    else:
        subprocess.terminate()  # in case the timeout was exceeded
        result = ProcessResult(
            error=f'Python subprocess did not respond in {timeout}s',
            json={'output': ''}
        )

    # we got our result; clean up like an assassin
    subprocess.terminate()  # TODO subprocess.kill() in Python 3.7
    subprocess.join()

    return result


def render(table: pandas.DataFrame, params: Params, **kwargs) -> ProcessResult:
    code: str = params['code']

    if not code.strip():
        # empty code, NOP
        return ProcessResult(table)

    return safe_eval_process(code, table)
