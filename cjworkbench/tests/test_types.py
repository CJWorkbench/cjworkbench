from datetime import datetime as dt
import unittest
from unittest import mock
import numpy as np
from pandas import DataFrame, Series
from pandas.testing import assert_series_equal
from cjworkbench.types import Column, ColumnType, ProcessResult, QuickFix, \
        TableShape


class ColumnTypeTextTests(unittest.TestCase):
    def test_text_type(self):
        series = Series(['x', np.nan, 'z'])
        column_type = ColumnType.TEXT()
        result = column_type.format_series(series)
        assert_series_equal(result, Series(['x', np.nan, 'z']))


class ColumnTypeNumberTests(unittest.TestCase):
    def test_default_format(self):
        series = Series([1.1, 2.231, np.nan, 3.0])
        column_type = ColumnType.NUMBER()
        result = column_type.format_series(series)
        assert_series_equal(result, Series(['1.1', '2.231', np.nan, '3.0']))

    def test_custom_format(self):
        series = Series([1.1, 2231, np.nan, 0.123])
        column_type = ColumnType.NUMBER(format='${:0,.2f}')
        result = column_type.format_series(series)
        assert_series_equal(result,
                            Series(['$1.10', '$2,231.00', np.nan, '$0.12']))

    def test_format_int_as_float(self):
        series = Series([1, 2, 3, 4], dtype=int)
        column_type = ColumnType.NUMBER(format='{:.1f}')
        result = column_type.format_series(series)
        assert_series_equal(result, Series(['1.0', '2.0', '3.0', '4.0']))

    def test_format_float_as_int(self):
        series = Series([1.1])
        column_type = ColumnType.NUMBER(format='{:d}')
        result = column_type.format_series(series)
        assert_series_equal(result, Series(['1']))

    def test_format_percent(self):
        series = Series([0.3, 11.111, 0.0001, np.nan])
        column_type = ColumnType.NUMBER(format='{:,.1%}')
        result = column_type.format_series(series)
        assert_series_equal(result,
                            Series(['30.0%', '1,111.1%', '0.0%', np.nan]))

    def test_format_int_as_percent(self):
        series = Series([1, 11])
        column_type = ColumnType.NUMBER(format='{:,.1%}')
        result = column_type.format_series(series)
        assert_series_equal(result, Series(['100.0%', '1,100.0%']))

    def test_format_zero_length_becomes_str(self):
        # (even though there's no way for pandas to detect type of result)
        # (luckily, pandas defaults to `object`)
        series = Series([], dtype=np.int64)
        result = ColumnType.NUMBER().format_series(series)
        assert_series_equal(result, Series([], dtype=object))

    def test_format_nulls_becomes_str(self):
        series = Series([np.nan, np.nan], dtype=np.float64)
        result = ColumnType.NUMBER().format_series(series)
        assert_series_equal(result, Series([np.nan, np.nan], dtype=object))

    def test_format_too_many_arguments(self):
        with self.assertRaisesRegex(ValueError, 'Can only format one number'):
            ColumnType.NUMBER('{:d}{:f}')

    def test_format_disallow_non_format(self):
        with self.assertRaisesRegex(ValueError,
                                    'Format must look like "{:...}"'):
            ColumnType.NUMBER('%d')

    def test_format_disallow_field_number(self):
        with self.assertRaisesRegex(ValueError,
                                    'Field names or numbers are not allowed'):
            ColumnType.NUMBER('{0:f}')

    def test_format_disallow_field_name(self):
        with self.assertRaisesRegex(ValueError,
                                    'Field names or numbers are not allowed'):
            ColumnType.NUMBER('{value:f}')

    def test_format_disallow_field_converter(self):
        with self.assertRaisesRegex(ValueError,
                                    'Field converters are not allowed'):
            ColumnType.NUMBER('{!r:f}')

    def test_format_disallow_invalid_type(self):
        with self.assertRaisesRegex(ValueError, "Unknown format code 'T'"):
            ColumnType.NUMBER('{:T}')


class ColumnTypeDatetimeTests(unittest.TestCase):
    def test_format(self):
        series = Series([dt(1999, 2, 3, 4, 5, 6, 7), np.nan,
                         dt(2000, 3, 4, 5, 6, 7, 8)])
        column_type = ColumnType.DATETIME()
        result = column_type.format_series(series)
        assert_series_equal(
            result,
            Series(['1999-02-03T04:05:06.000007Z', np.nan,
                    '2000-03-04T05:06:07.000008Z'])
        )


class ProcessResultTests(unittest.TestCase):
    def test_eq_none(self):
        self.assertNotEqual(ProcessResult(), None)

    def test_ctor_infer_columns(self):
        result = ProcessResult(DataFrame({
            'A': [1, 2],
            'B': ['x', 'y'],
            'C': [ np.nan, dt(2019, 3, 3, 4, 5, 6, 7) ],
        }))
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.TEXT()),
            Column('C', ColumnType.DATETIME()),
        ])

    def test_coerce_infer_columns(self):
        table = DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        result = ProcessResult.coerce(table)
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.TEXT()),
        ])

    def test_coerce_infer_columns_with_format(self):
        table = DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        result = ProcessResult.coerce({
            'dataframe': table,
            'column_formats': {'A': '{:,d}'},
        })
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER(format='{:,d}')),
            Column('B', ColumnType.TEXT()),
        ])

    def test_coerce_infer_columns_invalid_format_is_error(self):
        table = DataFrame({'A': [1, 2]})
        with self.assertRaisesRegex(ValueError,
                                    'Format must look like "{:...}"'):
            ProcessResult.coerce({
                'dataframe': table,
                'column_formats': {'A': 'x'}
            })

    def test_coerce_infer_columns_text_format_is_error(self):
        table = DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        with self.assertRaisesRegex(
            ValueError,
            '"format" not allowed for column "B" because it is of type "text"'
        ):
            ProcessResult.coerce({
                'dataframe': table,
                'column_formats': {'B': '{:,d}'},
            })

    def test_coerce_infer_columns_try_fallback_columns(self):
        table = DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        result = ProcessResult.coerce(table, try_fallback_columns=[
            Column('A', ColumnType.NUMBER('{:,d}')),
            Column('B', ColumnType.TEXT()),
        ])
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER('{:,d}')),
            Column('B', ColumnType.TEXT()),
        ])

    def test_coerce_infer_columns_try_fallback_columns_ignore_wrong_type(self):
        table = DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        result = ProcessResult.coerce(table, try_fallback_columns=[
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.NUMBER()),
        ])
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.TEXT()),
        ])

    def test_coerce_infer_columns_format_supercedes_try_fallback_columns(self):
        table = DataFrame({'A': [1, 2]})
        result = ProcessResult.coerce({
            'dataframe': DataFrame({'A': [1, 2]}),
            'column_formats': {'A': '{:,d}'},
        }, try_fallback_columns=[
            Column('A', ColumnType.NUMBER('{:,.2f}')),
        ])
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER('{:,d}')),
        ])

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
            'C': dt(2018, 8, 20),  # datetime64
        })
        df['D'] = Series(['cat'], dtype='category')
        result = ProcessResult(df)
        self.assertEqual(result.column_names, ['A', 'B', 'C', 'D'])
        self.assertEqual(result.columns, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.TEXT()),
            Column('C', ColumnType.DATETIME()),
            Column('D', ColumnType.TEXT()),
        ])

    def test_empty_columns(self):
        result = ProcessResult()
        self.assertEqual(result.column_names, [])
        self.assertEqual(result.columns, [])

    def test_table_shape(self):
        df = DataFrame({'A': [1, 2, 3]})
        result = ProcessResult(df)
        self.assertEqual(result.table_shape,
                         TableShape(3, [Column('A', ColumnType.NUMBER())]))

    def test_empty_table_shape(self):
        result = ProcessResult()
        self.assertEqual(result.table_shape, TableShape(0, []))
