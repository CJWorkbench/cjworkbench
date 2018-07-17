import unittest
from unittest import mock
from pandas import DataFrame
from server.modules.types import ProcessResult


class ProcessResultTests(unittest.TestCase):
    def test_eq_none(self):
        self.assertNotEqual(ProcessResult(), None)

    def test_coerce_processresult(self):
        expected = ProcessResult()
        result = ProcessResult.coerce(expected)
        self.assertIs(result, expected)

    def test_coerce_dataframe(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce(df)
        self.assertEqual(result, expected)

    def test_coerce_str(self):
        expected = ProcessResult(error='yay')
        result = ProcessResult.coerce('yay')
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(dataframe=df)
        result = ProcessResult.coerce((df, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(dataframe=df, error='hi')
        result = ProcessResult.coerce((df, 'hi'))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str(self):
        expected = ProcessResult(error='hi')
        result = ProcessResult.coerce((None, 'hi'))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_dict(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df, 'hi', {'a': 'b'})
        result = ProcessResult.coerce((df, 'hi', {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_none(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df, 'hi')
        result = ProcessResult.coerce((df, 'hi', None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_dict(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df, '', {'a': 'b'})
        result = ProcessResult.coerce((df, None, {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_none(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df)
        result = ProcessResult.coerce((df, None, None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_dict(self):
        expected = ProcessResult(error='hi', json={'a': 'b'})
        result = ProcessResult.coerce((None, 'hi', {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_str_none(self):
        expected = ProcessResult(error='hi')
        result = ProcessResult.coerce((None, 'hi', None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_none_dict(self):
        expected = ProcessResult(json={'a': 'b'})
        result = ProcessResult.coerce((None, None, {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_none_none_none(self):
        expected = ProcessResult()
        result = ProcessResult.coerce((None, None, None))
        self.assertEqual(result, expected)

    def test_coerce_bad_tuple(self):
        expected = ProcessResult(
            error='expected 2-tuple or 3-tuple; got 4-tuple'
        )
        result = ProcessResult.coerce(('foo', 'bar', 'baz', 'moo'))
        self.assertEqual(result, expected)

    def test_coerce_2tuple_no_dataframe(self):
        expected = ProcessResult(
            error='expected (DataFrame, str); got (str, str)'
        )
        result = ProcessResult.coerce(('foo', 'bar'))
        self.assertEqual(result, expected)

    def test_coerce_3tuple_no_dataframe(self):
        expected = ProcessResult(
            error='expected (DataFrame, str, dict); got (str, str, dict)'
        )
        result = ProcessResult.coerce(('foo', 'bar', {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_invalid_value(self):
        expected = ProcessResult(error='expected tuple; got list')
        result = ProcessResult.coerce([None, 'foo'])
        self.assertEqual(result, expected)

    def test_truncate_too_big_no_error(self):
        expected_df = DataFrame({'foo': ['bar', 'baz']})
        expected = ProcessResult(
            dataframe=expected_df,
            error='Truncated output from 3 rows to 2'
        )

        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2):
            result_df = DataFrame({'foo': ['bar', 'baz', 'moo']})
            result = ProcessResult(result_df, error='')
            result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_truncate_too_big_and_error(self):
        expected_df = DataFrame({'foo': ['bar', 'baz']})
        expected = ProcessResult(
            dataframe=expected_df,
            error='Some error\nTruncated output from 3 rows to 2'
        )

        with mock.patch('django.conf.settings.MAX_ROWS_PER_TABLE', 2):
            result_df = DataFrame({'foo': ['bar', 'baz', 'moo']})
            result = ProcessResult(result_df, error='Some error')
            result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_truncate_not_too_big(self):
        df = DataFrame({'foo': ['foo', 'bar', 'baz']})
        expected = ProcessResult(DataFrame(df))  # copy it
        result = ProcessResult(df)
        result.truncate_in_place_if_too_big()

        self.assertEqual(result, expected)

    def test_sanitize(self):
        expected = ProcessResult(DataFrame({'foo': ['[1]', '[2]']}))
        result = ProcessResult(DataFrame({'foo': [[1], [2]]}))
        result.sanitize_in_place()
        self.assertEqual(result, expected)
