import unittest
from cjwkernel.pandas.types import ProcessResult
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

    tc = unittest.TestCase()
    tc.assertEqual(actual.error, expected.error)
    tc.assertEqual(actual.columns, expected.columns)
    assert_frame_equal(actual.dataframe, expected.dataframe)
    tc.assertEqual(actual.json, expected.json)
    tc.assertEqual(actual.quick_fixes, expected.quick_fixes)
