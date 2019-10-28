import textwrap
import unittest
import pandas as pd
from cjwkernel.tests.pandas.util import assert_process_result_equal
from staticmodules.pythoncode import render, migrate_params


EMPTY_DATAFRAME = pd.DataFrame()
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


def eval_process(indented_code, table):
    code = textwrap.dedent(indented_code)
    return render(table, {"code": code})


class RenderTest(unittest.TestCase):
    def test_accept_and_return_dataframe(self):
        result = eval_process(
            """
            def process(table):
                return table * 2
            """,
            pd.DataFrame({"A": [1, 2]}),
        )
        assert_process_result_equal(
            result, (pd.DataFrame({"A": [2, 4]}), "", EMPTY_OUTPUT)
        )

    def test_return_str_for_error(self):
        result = eval_process(
            """
            def process(table):
                return 'hi'
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(result, (EMPTY_DATAFRAME, "hi", {"output": "hi"}))

    def test_builtins(self):
        # spot-check: do `list`, `sum` and `str` work the way we expect?
        result = eval_process(
            """
            def process(table):
                return str(sum(list([1, 2, 3])))
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(result, (EMPTY_DATAFRAME, "6", {"output": "6"}))

    def test_has_math(self):
        result = eval_process(
            """
            def process(table):
                return str(math.sqrt(4))
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(result, (EMPTY_DATAFRAME, "2.0", {"output": "2.0"}))

    def test_has_pandas_as_pd(self):
        result = eval_process(
            """
            def process(table):
                return pd.DataFrame({'A': [1, 2]})
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(
            result, (pd.DataFrame({"A": [1, 2]}), "", EMPTY_OUTPUT)
        )

    def test_has_numpy_as_np(self):
        result = eval_process(
            """
            def process(table):
                return pd.DataFrame({'A': np.array([1, 2])})
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(
            result, (pd.DataFrame({"A": [1, 2]}), "", EMPTY_OUTPUT)
        )

    def test_import(self):
        result = eval_process(
            """
            from typing import Dict

            def process(table):
                x: Dict[str, str] = {"x": "y"}
                return list(x.keys())[0]
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(result, (EMPTY_DATAFRAME, "x", {"output": "x"}))

    def test_print_is_captured(self):
        result = eval_process(
            """
            def process(table):
                print('hello')
                print('world')
                return table
            """,
            EMPTY_DATAFRAME,
        )
        assert_process_result_equal(result, {"json": {"output": "hello\nworld\n"}})

    def test_syntax_error(self):
        result = eval_process(
            """
            def process(table):
                return ta(
            """,
            EMPTY_DATAFRAME,
        )
        text = "Line 3: unexpected EOF while parsing (your code, line 3)"
        assert_process_result_equal(result, (EMPTY_DATAFRAME, text, {"output": text}))

    def test_error_during_process(self):
        result = eval_process(
            """
            def process(table):
                return ta()
            """,
            EMPTY_DATAFRAME,
        )
        trace = """Traceback (most recent call last):
  File "your code", line 3, in process
NameError: name 'ta' is not defined
"""
        text = "Line 3: NameError: name 'ta' is not defined"
        assert_process_result_equal(
            result, (EMPTY_DATAFRAME, text, {"output": trace + text})
        )

    def test_missing_process(self):
        result = eval_process(
            """
            def xprocess(table):
                return table
            """,
            EMPTY_DATAFRAME,
        )
        text = 'Please define a "process(table)" function'
        assert_process_result_equal(result, (EMPTY_DATAFRAME, text, {"output": text}))

    def test_bad_process_signature(self):
        result = eval_process(
            """
            def process(table, params):
                return table
            """,
            EMPTY_DATAFRAME,
        )
        text = "Please make your process(table) function accept exactly 1 argument"
        assert_process_result_equal(result, (EMPTY_DATAFRAME, text, {"output": text}))

    def test_invalid_retval(self):
        result = eval_process(
            """
            def process(table):
                return None
            """,
            EMPTY_DATAFRAME,
        )
        text = (
            "Please make process(table) return a pd.DataFrame. "
            "(Yours returned a NoneType.)"
        )
        assert_process_result_equal(result, (EMPTY_DATAFRAME, text, {"output": text}))
