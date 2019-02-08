import datetime
import unittest
from unittest import mock
from pandas import DataFrame, Series
from cjworkbench.types import Column, ColumnType, ProcessResult, QuickFix, \
        TableShape


class ProcessResultTests(unittest.TestCase):
    def test_eq_none(self):
        self.assertNotEqual(ProcessResult(), None)

    def test_coerce_none(self):
        result = ProcessResult.coerce(None)
        expected = ProcessResult(dataframe=DataFrame())
        self.assertEqual(result, expected)

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
        expected = ProcessResult(df, 'hi', json={'a': 'b'})
        result = ProcessResult.coerce((df, 'hi', {'a': 'b'}))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_str_none(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df, 'hi')
        result = ProcessResult.coerce((df, 'hi', None))
        self.assertEqual(result, expected)

    def test_coerce_tuple_dataframe_none_dict(self):
        df = DataFrame({'foo': ['bar']})
        expected = ProcessResult(df, '', json={'a': 'b'})
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
        result = ProcessResult.coerce(('foo', 'bar', 'baz', 'moo'))
        self.assertIsNotNone(result.error)

    def test_coerce_2tuple_no_dataframe(self):
        result = ProcessResult.coerce(('foo', 'bar'))
        self.assertIsNotNone(result.error)

    def test_coerce_3tuple_no_dataframe(self):
        result = ProcessResult.coerce(('foo', 'bar', {'a': 'b'}))
        self.assertIsNotNone(result.error)

    def test_coerce_dict_with_quickfix_tuple(self):
        dataframe = DataFrame({'A': [1, 2]})
        quick_fix = QuickFix('Hi', 'prependModule',
                             ['texttodate', {'column': 'created_at'}])
        result = ProcessResult.coerce({
            'dataframe': dataframe,
            'error': 'an error',
            'json': {'foo': 'bar'},
            'quick_fixes': [
                ('Hi', 'prependModule', 'texttodate',
                 {'column': 'created_at'}),
            ]
        })
        expected = ProcessResult(dataframe, 'an error', json={'foo': 'bar'},
                                 quick_fixes=[quick_fix])
        self.assertEqual(result, expected)

    def test_coerce_dict_with_quickfix_dict(self):
        dataframe = DataFrame({'A': [1, 2]})
        quick_fix = QuickFix('Hi', 'prependModule',
                             ['texttodate', {'column': 'created_at'}])
        result = ProcessResult.coerce({
            'dataframe': dataframe,
            'error': 'an error',
            'json': {'foo': 'bar'},
            'quick_fixes': [
                {
                    'text': 'Hi',
                    'action': 'prependModule',
                    'args': ['texttodate', {'column': 'created_at'}],
                },
            ]
        })
        expected = ProcessResult(dataframe, 'an error', json={'foo': 'bar'},
                                 quick_fixes=[quick_fix])
        self.assertEqual(result, expected)

    def test_coerce_dict_bad_quickfix_dict(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce({
                'error': 'an error',
                'json': {'foo': 'bar'},
                'quick_fixes': [
                    {
                        'text': 'Hi',
                        'action': 'prependModule',
                        'arguments': ['texttodate', {'column': 'created_at'}],
                    },
                ]
            })

    def test_coerce_dict_wrong_key(self):
        with self.assertRaises(ValueError):
            ProcessResult.coerce({'table': DataFrame({'A': [1]})})

    def test_coerce_empty_dict(self):
        result = ProcessResult.coerce({})
        expected = ProcessResult()
        self.assertEqual(result, expected)

    def test_coerce_invalid_value(self):
        result = ProcessResult.coerce([None, 'foo'])
        self.assertIsNotNone(result.error)

    def test_status_ok(self):
        result = ProcessResult(DataFrame({'A': [1]}), '')
        self.assertEqual(result.status, 'ok')

    def test_status_ok_with_warning(self):
        result = ProcessResult(DataFrame({'A': [1]}), 'warning')
        self.assertEqual(result.status, 'ok')

    def test_status_ok_with_no_rows(self):
        result = ProcessResult(DataFrame({'A': []}), '')
        self.assertEqual(result.status, 'ok')

    def test_status_error(self):
        result = ProcessResult(DataFrame(), 'error')
        self.assertEqual(result.status, 'error')

    def test_status_unreachable(self):
        result = ProcessResult(DataFrame(), '')
        self.assertEqual(result.status, 'unreachable')

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

    def test_columns(self):
        df = DataFrame({
            'A': [1],  # number
            'B': ['foo'],  # str
            'C': datetime.datetime(2018, 8, 20),  # datetime64
        })
        df['D'] = Series(['cat'], dtype='category')
        result = ProcessResult(df)
        self.assertEqual(result.column_names, ['A', 'B', 'C', 'D'])
        self.assertEqual(result.column_types, [
            ColumnType.NUMBER,
            ColumnType.TEXT,
            ColumnType.DATETIME,
            ColumnType.TEXT,
        ])
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER),
            Column('B', ColumnType.TEXT),
            Column('C', ColumnType.DATETIME),
            Column('D', ColumnType.TEXT),
        ])

    def test_empty_columns(self):
        result = ProcessResult()
        self.assertEqual(result.column_names, [])
        self.assertEqual(result.column_types, [])
        self.assertEqual(result.columns, [])

    def test_table_shape(self):
        df = DataFrame({'A': [1, 2, 3]})
        result = ProcessResult(df)
        self.assertEqual(result.table_shape,
                         TableShape(3, [Column('A', ColumnType.NUMBER)]))

    def test_empty_table_shape(self):
        result = ProcessResult()
        self.assertEqual(result.table_shape, TableShape(0, []))
