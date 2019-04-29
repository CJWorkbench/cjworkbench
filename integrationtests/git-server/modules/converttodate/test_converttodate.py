import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from converttodate import render, migrate_params


class MigrateParamsTests(unittest.TestCase):
    def test_v0(self):
        result = migrate_params({
            'colnames': 'report_date',
            'type_date': 1,
            'type_null': True
        })
        self.assertEqual(result, {
            'colnames': 'report_date',
            'input_format': 'us',
            'error_means_null': True
        })

    def test_v1(self):
        result = migrate_params({
            'colnames': 'report_date',
            'input_format': 'us',
            'error_means_null': True
        })
        self.assertEqual(result, {
            'colnames': 'report_date',
            'input_format': 'us',
            'error_means_null': True
        })


def P(colnames='', input_format='auto', error_means_null=True):
    """Factory method to build params dict."""
    return {
        'colnames': colnames,
        'input_format': input_format,
        'error_means_null': error_means_null,
    }


class ConverttodateTests(unittest.TestCase):
    def test_no_column_no_op(self):
        # should NOP when first applied
        table = pd.DataFrame({'A': [1, 2]})
        params = {'colnames': ''}
        result = render(table.copy(), params)
        assert_frame_equal(result, table)

    def test_us(self):
        # All values should have the same date
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'A': ['08/07/2018', ' 08/07/2018T00:00:00 ',
                  '..08/07/2018T00:00:00:00..']
        })
        expected = pd.DataFrame({'A': [reference_date] * 3})
        result = render(table.copy(), P('A', 'us'))
        assert_frame_equal(result, expected)

    def test_eu(self):
        # All values should have the same date
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'A': ['07/08/2018', ' 07/08/2018T00:00:00 ',
                  '..07/08/2018T00:00:00..'],
        })
        expected = pd.DataFrame({'A': [reference_date] * 3})
        result = render(table.copy(), P('A', 'eu'))
        assert_frame_equal(result, expected)

    def test_numbers(self):
        # For now, assume value is year and cast to string
        table = pd.DataFrame({'number': [2018, 1960, 99999]})
        expected = pd.DataFrame({
            'number': [
                np.datetime64('2018-01-01T00:00:00.000000000'),
                np.datetime64('1960-01-01T00:00:00.000000000'),
                pd.NaT,
            ]
        })

        result = render(table.copy(), P('number', 'auto', True))
        assert_frame_equal(result, expected)

    def test_iso8601_tz_aware_plus_non_tz_aware(self):
        table = pd.DataFrame({
            'A': ['2019-01-01T00:00:00.000', '2019-03-02T12:02:13.000Z']
        }, dtype='category')
        result = render(table, P('A', 'auto'))
        assert_frame_equal(
            result,
            pd.DataFrame({'A': [
                np.datetime64('2019-01-01T00:00:00.000'),
                np.datetime64('2019-03-02T12:02:13.000'),
            ]})
        )

    def test_auto(self):
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'written': ['August 7, 2018', 'August 07, 2018',
                        'August 07, 2018'],
            'yearfirst': ['2018-08-07', ' 2018.08.07T00:00:00 ',
                          '..2018.08.07T00:00:00..'],
        })
        expected = pd.DataFrame({
            'written': [reference_date] * 3,
            'yearfirst': [reference_date] * 3,
        })
        result = render(table.copy(), P('written,yearfirst', 'auto', True))
        assert_frame_equal(result, expected)

    def test_date_input(self):
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'A': [reference_date, pd.NaT, reference_date]
        })
        expected = table.copy()
        result = render(table.copy(), P('A', 'auto', False))
        assert_frame_equal(result, expected)

    def test_multi_types_error(self):
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'A': [reference_date, pd.NaT, reference_date],
            'B': ['not a date', 'another bad date', 'no way'],
        })
        result = render(table.copy(), P('A,B', 'auto', False))
        self.assertEqual(result, (
            "'not a date' in row 1 of 'B' cannot be converted. Overall, there "
            "are 3 errors in 1 column. Select 'non-dates to null' to set "
            'these values to null'
        ))

    def test_categories(self):
        reference_date = np.datetime64('2018-08-07T00:00:00')
        table = pd.DataFrame({
            'A': ['August 7, 2018', None, 'T8'],
        }, dtype='category')
        expected = pd.DataFrame({
            'A': [reference_date, pd.NaT, pd.NaT],
        })
        result = render(table.copy(), P('A', 'auto', True))
        assert_frame_equal(result, expected)

    def test_null_input_is_not_error(self):
        table = pd.DataFrame({'null': ['08/07/2018', None, 99]})
        result = render(table, P('null', 'auto', False))
        self.assertEqual(result, (
            "'99' in row 3 of 'null' cannot be converted. Overall, there "
            "is 1 error in 1 column. Select 'non-dates to null' to set "
            'these values to null'
        ))

    def test_error(self):
        table = pd.DataFrame({'null': ['08/07/2018', '99', '98']})
        result = render(table, P('null', 'auto', False))
        self.assertEqual(result, (
            "'99' in row 2 of 'null' cannot be converted. Overall, there "
            "are 2 errors in 1 column. Select 'non-dates to null' to set "
            'these values to null'
        ))

    def test_error_multicolumn(self):
        table = pd.DataFrame({
            'null': ['08/07/2018', '99', '99'],
            'number': [1960, 2018, 99999],
        })
        result = render(table, P('null,number', 'auto', False))

        self.assertEqual(result, (
            "'99' in row 2 of 'null' cannot be converted. Overall, there "
            "are 3 errors in 2 columns. Select 'non-dates to null' to set "
            'these values to null'
        ))


if __name__ == '__main__':
    unittest.main()
