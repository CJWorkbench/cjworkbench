import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from converttodate import render

reference_date = np.datetime64('2018-08-07T00:00:00')

class TestConvertDate(unittest.TestCase):
    def test_no_column_no_op(self):
        # should NOP when first applied
        table = pd.DataFrame({'A': [1, 2]})
        params = {'colnames': ''}
        result = render(table.copy(), params)
        assert_frame_equal(result, table)

    def test_us(self):
        # All values should have the same date
        table = pd.DataFrame({
            'us': ['08/07/2018', ' 08/07/2018T00:00:00 ',
                   '..08/07/2018T00:00:00:00..']
        })
        params = {'colnames': 'us', 'type_null': True, 'type_date': 1}
        expected = pd.DataFrame({'us': [reference_date] * 3})
        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_eu(self):
        # All values should have the same date
        table = pd.DataFrame({
            'eu': ['07/08/2018', ' 07/08/2018T00:00:00 ',
                   '..07/08/2018T00:00:00..'],
        })
        params = {'colnames': 'eu', 'type_null': True, 'type_date': 2}
        expected = pd.DataFrame({'eu': [reference_date] * 3})
        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_numbers(self):
        # For now, assume value is year and cast to string
        table = pd.DataFrame({
            'number': [2018, 1960, 99999],
        })
        params = {'colnames': 'number', 'type_null': True, 'type_date': 0}
        expected = pd.DataFrame({
            'number': [
                np.datetime64('2018-01-01T00:00:00.000000000'),
                np.datetime64('1960-01-01T00:00:00.000000000'),
                pd.NaT,
            ]
        })

        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_auto(self):
        table = pd.DataFrame({
            'written': ['August 7, 2018', 'August 07, 2018',
                        'August 07, 2018'],
            'yearfirst': ['2018-08-07', ' 2018.08.07T00:00:00 ',
                          '..2018.08.07T00:00:00..'],
        })
        params = {'colnames': 'written,yearfirst', 'type_null': True,
                  'type_date': 0}
        expected = pd.DataFrame({
            'written': [reference_date] * 3,
            'yearfirst': [reference_date] * 3,
        })

        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_date_input(self):
        table = pd.DataFrame({
            'A': [reference_date, pd.NaT, reference_date]
        })
        params = {'colnames': 'A', 'type_null': False, 'type_date': 0}
        expected = table.copy()
        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_multi_types_error(self):
        table = pd.DataFrame({
            'A': [reference_date, pd.NaT, reference_date],
            'B': ['not a date', 'another bad date', 'no way'],
        })
        params = {'colnames': 'A,B', 'type_null': False, 'type_date': 0}
        expected = table.copy()
        result = render(table.copy(), params)
        self.assertEqual(result, (None, (
            "'not a date' in row 1 of 'B' cannot be converted. Overall, there "
            "are 3 errors in 1 column. Select 'non-dates to null' to set "
            'these values to null'
        )))

    def test_categories(self):
        table = pd.DataFrame({
            'A': ['August 7, 2018', None, 'T8'],
        }, dtype='category')
        params = {'colnames': 'A', 'type_null': True, 'type_date': 0}
        expected = pd.DataFrame({
            'A': [reference_date, pd.NaT, pd.NaT],
        })

        result = render(table.copy(), params)
        assert_frame_equal(result, expected)

    def test_null_input_is_not_error(self):
        table = pd.DataFrame({'null': ['08/07/2018', None, 99]})
        params = {'colnames': 'null', 'type_null': False, 'type_date': 0}

        self.assertEqual(render(table.copy(), params), (
            None,
            (
                "'99' in row 3 of 'null' cannot be converted. Overall, there "
                "is 1 error in 1 column. Select 'non-dates to null' to set "
                'these values to null'
            )
        ))

    def test_error(self):
        table = pd.DataFrame({'null': ['08/07/2018', '99', '98']})
        params = {'colnames': 'null', 'type_null': False, 'type_date': 0}

        self.assertEqual(render(table.copy(), params), (
            None,
            (
                "'99' in row 2 of 'null' cannot be converted. Overall, there "
                "are 2 errors in 1 column. Select 'non-dates to null' to set "
                'these values to null'
            )
        ))

    def test_error_multicolumn(self):
        table = pd.DataFrame({
            'null': ['08/07/2018', '99', '99'],
            'number': [1960, 2018, 99999],
        })
        params = {'colnames': 'null,number', 'type_null': False,
                  'type_date': 0}

        self.assertEqual(render(table.copy(), params), (
            None,
            (
                "'99' in row 2 of 'null' cannot be converted. Overall, there "
                "are 3 errors in 2 columns. Select 'non-dates to null' to set "
                'these values to null'
            )
        ))

if __name__ == '__main__':
    unittest.main()
