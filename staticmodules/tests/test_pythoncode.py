import unittest
import pandas
from pandas.testing import assert_frame_equal
from staticmodules.pythoncode import safe_eval_process, migrate_params


EMPTY_DATAFRAME = pandas.DataFrame()
EMPTY_OUTPUT = {"output": ""}


class MigrateParamsTest(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(
            migrate_params({"run": "", "code": "def process(x):\n  return x"}),
            {"code": "def process(x):\n  return x"},
        )

    def test_v1(self):
        self.assertEqual(
            migrate_params({"code": "def process(x):\n  return x"}),
            {"code": "def process(x):\n  return x"},
        )


class SafeEvalProcessTest(unittest.TestCase):
    def test_pipe_dataframe(self):
        dataframe = pandas.DataFrame({"a": [1, 2]})
        result = safe_eval_process(
            """
def process(table):
    return table
""",
            dataframe.copy(),
        )
        self.assertEqual(result.error, "")
        assert_frame_equal(result.dataframe, dataframe)
        self.assertEqual(result.json, EMPTY_OUTPUT)

    def test_return_str_for_error(self):
        result = safe_eval_process(
            """
def process(table):
    return 'hi'
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(result.error, "hi")
        assert_frame_equal(result.dataframe, EMPTY_DATAFRAME)
        self.assertEqual(result.json, EMPTY_OUTPUT)

    def test_builtins(self):
        # spot-check: do `list`, `sum` and `str` work the way we expect?
        result = safe_eval_process(
            """
def process(table):
    return str(sum(list([1, 2, 3])))
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(result.error, "6")

    def test_has_math(self):
        result = safe_eval_process(
            """
def process(table):
    return str(math.sqrt(4))
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(result.error, "2.0")

    def test_has_pandas_as_pd(self):
        result = safe_eval_process(
            """
def process(table):
    return pd.DataFrame({'A': [1, 2]})
""",
            EMPTY_DATAFRAME,
        )
        assert_frame_equal(result.dataframe, pandas.DataFrame({"A": [1, 2]}))

    def test_has_numpy_as_np(self):
        result = safe_eval_process(
            """
def process(table):
    return pd.DataFrame({'A': np.array([1, 2])})
""",
            EMPTY_DATAFRAME,
        )
        assert_frame_equal(result.dataframe, pandas.DataFrame({"A": [1, 2]}))

    def test_import_disabled(self):
        result = safe_eval_process(
            """
import typing

def process(table):
    return 'should not arrive here'
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(
            result.error,
            ("Line 2: PythonFeatureDisabledError: " "builtins.__import__ is disabled"),
        )
        self.assertEqual(
            result.json,
            {
                "output": """Traceback (most recent call last):
  File "user input", line 2, in <module>
PythonFeatureDisabledError: builtins.__import__ is disabled
"""
            },
        )

    def test_builtins_disabled(self):
        result = safe_eval_process(
            """
def process(table):
    return eval('foo')
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(
            result.error,
            ("Line 3: PythonFeatureDisabledError: builtins.eval is disabled"),
        )
        self.assertEqual(
            result.json,
            {
                "output": """Traceback (most recent call last):
  File "user input", line 3, in process
PythonFeatureDisabledError: builtins.eval is disabled
"""
            },
        )

    def test_print_is_captured(self):
        result = safe_eval_process(
            """
def process(table):
    print('hello')
    print('world')
    return table
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(result.json, {"output": "hello\nworld\n"})

    def test_syntax_error(self):
        result = safe_eval_process(
            """
def process(table):
    return ta(
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(
            result.error, ("Line 3: unexpected EOF while parsing (user input, line 3)")
        )
        self.assertEqual(result.json, EMPTY_OUTPUT)

    def test_missing_process(self):
        result = safe_eval_process(
            """
def xprocess(table):
    return table
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(result.error, 'You must define a "process" function')

    def test_bad_process_signature(self):
        result = safe_eval_process(
            """
def process(table, params):
    return table
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(
            result.error, 'Your "process" function must accept exactly one argument'
        )

    def test_kill_after_timeout(self):
        result = safe_eval_process(
            """
def process(table):
    while True:
        pass  # infinite loop!
""",
            EMPTY_DATAFRAME,
            timeout=0.0001,
        )
        self.assertEqual(result.error, "Python subprocess did not respond in 0.0001s")

    def test_invalid_retval(self):
        result = safe_eval_process(
            """
def process(table):
    return None
""",
            EMPTY_DATAFRAME,
        )
        self.assertEqual(
            result.error, "process(table) did not return a pd.DataFrame or a str"
        )
        self.assertEqual(
            result.json,
            {"output": "process(table) did not return a pd.DataFrame or a str\n"},
        )


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
