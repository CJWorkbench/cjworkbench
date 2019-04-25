import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules import pastecsv
from .util import MockParams


P = MockParams.factory(csv='', has_header_row=True)


def render(params):
    return pastecsv.render(pd.DataFrame(), params)


class PasteCSVTests(unittest.TestCase):
    def test_empty(self):
        result = render(P(csv='', has_header_row=True))
        assert_frame_equal(result, pd.DataFrame())

    def test_csv(self):
        result = render(P(csv='A,B\n1,foo\n2,bar'))
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': pd.Series(['foo', 'bar'], dtype='category'),
        })
        assert_frame_equal(result, expected)

    def test_tsv(self):
        result = render(P(csv='A\tB\n1\tfoo\n2\tbar'))
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': pd.Series(['foo', 'bar'], dtype='category'),
        })
        assert_frame_equal(result, expected)

    def test_extra_data_should_not_mangle_index(self):
        # Pandas' default behavior is _really_ weird when the number of values
        # in a row exceeds the number of headers. It tries building a
        # MultiIndex out of the first ones. This is probably so it can read its
        # own string representations? ... but it's terrible for our users.
        result = render(P(csv='A,B\na,b,c', has_header_row=True))
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a'],
            'B': ['b'],
        }, dtype='category'))

    def test_list_index_out_of_range(self):
        # Pandas' read_csv() freaks out on even the simplest examples....
        #
        # Today's exhibit:
        # pd.read_csv(io.StringIO('A\n,,'), index_col=False)
        # raises IndexError: list index out of range
        result = render(P(csv='A\n,,', has_header_row=True))
        assert_frame_equal(result, pd.DataFrame({'A': ['']}, dtype='category'))

    def test_no_header(self):
        result = render(P(csv='A,B', has_header_row=False))
        assert_frame_equal(result, pd.DataFrame({
            'Column 1': ['A'],
            'Column 2': ['B'],
        }, dtype='category'))

    def test_duplicate_column_names_is_error(self):
        result = render(P(csv='A,A\n1,2', has_header_row=True))
        self.assertEqual(result, (
            'Duplicate column name "A". Please edit the first line '
            'so there are no repeated column names.'
        ))

    def test_auto_column_names_when_not_given(self):
        result = render(P(csv='A,,B\n1,2,3', has_header_row=True))
        assert_frame_equal(result, pd.DataFrame({
            'A': [1],
            'Column 2': [2],
            'B': [3],
        }))

    def test_no_nan(self):
        # https://www.pivotaltracker.com/story/show/163106728
        result = render(P(csv='A,B\nx,y\nz,NA'))
        expected = pd.DataFrame({
            'A': ['x', 'z'],
            'B': ['y', 'NA'],
        }, dtype='category')
        assert_frame_equal(result, expected)
