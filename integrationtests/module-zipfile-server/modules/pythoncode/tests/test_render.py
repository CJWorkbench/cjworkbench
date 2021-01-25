import textwrap

import pandas as pd
from pandas.testing import assert_frame_equal

from pythoncode import render

EMPTY_DATAFRAME = pd.DataFrame()
EMPTY_OUTPUT = {"output": ""}


def assert_result_equal(
    actual, expected_dataframe, expected_error, expected_json
) -> None:
    actual_dataframe, actual_error, actual_json = actual

    # Edge case: comparing zero-length tables....
    # pd.RangeIndex(0).equals(pd.Index([])) is True, but
    # assert_frame_equal(pd.DataFrame(), pd.DataFrame().reset_index(drop=True))
    # raises an error because it considers pd.RangeIndex(0) and pd.Index([]) to
    # be different. In Workbench, they're interchangeable; and we don't want to
    # force a module to output one or the other because it's annoying. So if
    # they're both empty tables with identical indexes, pass.
    if actual_dataframe.index.equals(
        pd.RangeIndex(0)
    ) and expected_dataframe.index.equals(pd.RangeIndex(0)):
        expected_dataframe = expected_dataframe.set_index(actual_dataframe.index)

    assert actual_error == expected_error
    assert_frame_equal(actual_dataframe, expected_dataframe)
    assert actual_json == expected_json


def eval_process(indented_code, table):
    code = textwrap.dedent(indented_code)
    return render(table, {"code": code})


def test_accept_and_return_dataframe():
    result = eval_process(
        """
        def process(table):
            return table * 2
        """,
        pd.DataFrame({"A": [1, 2]}),
    )
    assert_result_equal(result, pd.DataFrame({"A": [2, 4]}), "", EMPTY_OUTPUT)


def test_return_str_for_error():
    result = eval_process(
        """
        def process(table):
            return 'hi'
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, EMPTY_DATAFRAME, "hi", {"output": "hi"})


def test_builtins():
    # spot-check: do `list`, `sum` and `str` work the way we expect?
    result = eval_process(
        """
        def process(table):
            return str(sum(list([1, 2, 3])))
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, EMPTY_DATAFRAME, "6", {"output": "6"})


def test_has_math():
    result = eval_process(
        """
        def process(table):
            return str(math.sqrt(4))
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, EMPTY_DATAFRAME, "2.0", {"output": "2.0"})


def test_has_pandas_as_pd():
    result = eval_process(
        """
        def process(table):
            return pd.DataFrame({'A': [1, 2]})
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, pd.DataFrame({"A": [1, 2]}), "", EMPTY_OUTPUT)


def test_has_numpy_as_np():
    result = eval_process(
        """
        def process(table):
            return pd.DataFrame({'A': np.array([1, 2])})
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, pd.DataFrame({"A": [1, 2]}), "", EMPTY_OUTPUT)


def test_import():
    result = eval_process(
        """
        from typing import Dict

        def process(table):
            x: Dict[str, str] = {"x": "y"}
            return list(x.keys())[0]
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, EMPTY_DATAFRAME, "x", {"output": "x"})


def test_print_is_captured():
    result = eval_process(
        """
        def process(table):
            print('hello')
            print('world')
            return table
        """,
        EMPTY_DATAFRAME,
    )
    assert_result_equal(result, EMPTY_DATAFRAME, "", {"output": "hello\nworld\n"})


def test_syntax_error():
    result = eval_process(
        """
        def process(table):
            return ta(
        """,
        EMPTY_DATAFRAME,
    )
    text = "Line 3: unexpected EOF while parsing (your code, line 3)"
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_null_bytes():
    result = eval_process(
        """
        def process(table):
            return \x00"hi"
        """,
        EMPTY_DATAFRAME,
    )
    text = "Your code contains null bytes"
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_error_during_process():
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
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": trace + text})


def test_missing_process():
    result = eval_process(
        """
        def xprocess(table):
            return table
        """,
        EMPTY_DATAFRAME,
    )
    text = 'Please define a "process(table)" function'
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_bad_process_signature():
    result = eval_process(
        """
        def process(table, params):
            return table
        """,
        EMPTY_DATAFRAME,
    )
    text = "Please make your process(table) function accept exactly 1 argument"
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_invalid_retval():
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
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_unhandled_dataframe_retval():
    result = eval_process(
        """
        def process(table):
            return pd.DataFrame({"A": [1]}, index=["hi"])
        """,
        EMPTY_DATAFRAME,
    )
    # Error message is from cjwpandasmodule.validate
    text = "Unhandled DataFrame: must use the default RangeIndex — try table.reset_index(drop=True, inplace=True)"
    assert_result_equal(result, EMPTY_DATAFRAME, text, {"output": text})


def test_empty_code_is_noop():
    result = eval_process(
        """
        """,
        pd.DataFrame({"A": [1]}),
    )
    assert_result_equal(result, pd.DataFrame({"A": [1]}), "", EMPTY_OUTPUT)
