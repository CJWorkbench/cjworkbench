from dataclasses import replace
import unittest
from cjwkernel.pandas.types import ProcessResult
import pandas as pd
from pandas.testing import assert_frame_equal


def assert_process_result_equal(actual, expected) -> None:
    """
    Assert `ProcessResult.coerce(actual) == ProcessResult.coerce(expected)`

    Raise AssertionError otherwise.

    The use case: `actual` is the return value from a Pandas module's `fetch()`
    or `render()`: maybe an `str`, maybe a `pd.DataFrame`, maybe a
    """
    actual = ProcessResult.coerce(actual)
    expected = ProcessResult.coerce(expected)

    # Edge case: comparing zero-length tables....
    # pd.RangeIndex(0).equals(pd.Index([])) is True, but
    # assert_frame_equal(pd.DataFrame(), pd.DataFrame().reset_index(drop=True))
    # raises an error because it considers pd.RangeIndex(0) and pd.Index([]) to
    # be different. In Workbench, they're interchangeable; and we don't want to
    # force a module to output one or the other because it's annoying. So if
    # they're both empty tables with identical indexes, pass.
    if actual.dataframe.index.equals(
        pd.RangeIndex(0)
    ) and expected.dataframe.index.equals(pd.RangeIndex(0)):
        expected = replace(
            expected, dataframe=expected.dataframe.set_index(actual.dataframe.index)
        )

    tc = unittest.TestCase()
    tc.assertEqual(actual.errors, expected.errors)
    tc.assertEqual(actual.columns, expected.columns)
    assert_frame_equal(actual.dataframe, expected.dataframe)
    tc.assertEqual(actual.json, expected.json)
