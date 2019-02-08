import unittest
import numpy
import pandas
from cjworkbench.types import ProcessResult
from server.modules.pythoncode import safe_eval_process


EMPTY_DATAFRAME = pandas.DataFrame()
EMPTY_OUTPUT = {'output': ''}


class SafeEvalProcessTest(unittest.TestCase):
    def test_pickle(self):
        dataframe = pandas.DataFrame({'a': [1, 2]})
        result = safe_eval_process("""
def process(table):
    return table
""", dataframe)
        self.assertEqual(result, ProcessResult(dataframe, json=EMPTY_OUTPUT))

    def test_return_str_for_error(self):
        result = safe_eval_process("""
def process(table):
    return 'hi'
""", EMPTY_DATAFRAME)
        self.assertEqual(result, ProcessResult(error='hi', json=EMPTY_OUTPUT))

    def test_builtins(self):
        # spot-check: do `list`, `sum` and `str` work the way we expect?
        result = safe_eval_process("""
def process(table):
    return str(sum(list([1, 2, 3])))
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(error='6', json=EMPTY_OUTPUT))

    def test_has_math(self):
        result = safe_eval_process("""
def process(table):
    return str(math.sqrt(4))
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(error='2.0', json=EMPTY_OUTPUT))

    def test_has_pandas_as_pd(self):
        result = safe_eval_process("""
def process(table):
    return pd.DataFrame({'a': [1, 2]})
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            dataframe=pandas.DataFrame({'a': [1, 2]}),
            json=EMPTY_OUTPUT
        ))

    def test_has_numpy_as_np(self):
        result = safe_eval_process("""
def process(table):
    return pd.DataFrame({'a': np.array([1, 2])})
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            dataframe=pandas.DataFrame({'a': numpy.array([1, 2])}),
            json=EMPTY_OUTPUT
        ))

    def test_import_disabled(self):
        result = safe_eval_process("""
import typing

def process(table):
    return 'should not arrive here'
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error=(
                'Line 2: PythonFeatureDisabledError: '
                'builtins.__import__ is disabled'
            ),
            json={'output': """Traceback (most recent call last):
  File "user input", line 2, in <module>
PythonFeatureDisabledError: builtins.__import__ is disabled
"""}
        ))

    def test_builtins_disabled(self):
        result = safe_eval_process("""
def process(table):
    return eval('foo')
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error=(
                'Line 3: PythonFeatureDisabledError: builtins.eval is disabled'
            ),
            json={'output': """Traceback (most recent call last):
  File "user input", line 3, in process
PythonFeatureDisabledError: builtins.eval is disabled
"""}
        ))

    def test_print_is_captured(self):
        result = safe_eval_process("""
def process(table):
    print('hello')
    print('world')
    return table
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            json={'output': 'hello\nworld\n'}
        ))

    def test_syntax_error(self):
        result = safe_eval_process("""
def process(table):
    return ta(
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error=(
                'Line 3: unexpected EOF while parsing '
                '(user input, line 3)'
            ),
            json=EMPTY_OUTPUT
        ))

    def test_missing_process(self):
        result = safe_eval_process("""
def xprocess(table):
    return table
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error='You must define a "process" function',
            json=EMPTY_OUTPUT
        ))

    def test_bad_process_signature(self):
        result = safe_eval_process("""
def process(table, params):
    return table
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error='Your "process" function must accept exactly one argument',
            json=EMPTY_OUTPUT
        ))

    def test_kill_after_timeout(self):
        result = safe_eval_process("""
def process(table):
    while True:
        pass  # infinite loop!
""", EMPTY_DATAFRAME, timeout=0.0001)

        self.assertEqual(result, ProcessResult(
            error='Python subprocess did not respond in 0.0001s',
            json=EMPTY_OUTPUT
        ))

    def test_invalid_retval(self):
        result = safe_eval_process("""
def process(table):
    return None
""", EMPTY_DATAFRAME)

        self.assertEqual(result, ProcessResult(
            error='process(table) did not return a pd.DataFrame or a str',
            json={'output': (
                'process(table) did not return a pd.DataFrame or a str\n'
            )}
        ))


#     def test_builtins_disabled_within_pandas(self):
#         result = safe_eval_process("""
# def process(table):
#     return pd.read_csv('/some/file')
# """, EMPTY_DATAFRAME)
#
#         self.assertEqual(result, ProcessResult(
#             error=(
#                 'Line 3: PythonFeatureDisabledError: '
#                 'builtins.open is disabled'
#             ),
#             json=EMPTY_OUTPUT
#         ))
