import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.modules import pastecsv
from .util import MockParams


P = MockParams.factory(csv='', has_header_row=True)


def render(params):
    result = pastecsv.render(pd.DataFrame(), params)
    result = ProcessResult.coerce(result)
    return result


class PasteCSVTests(unittest.TestCase):
    def test_empty(self):
        result = render(P(csv='', has_header_row=True))
        self.assertEqual(result, ProcessResult())

    def test_csv(self):
        result = render(P(csv='A,B\n1,foo\n2,bar'))
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': ['foo', 'bar']
        })
        self.assertEqual(result, ProcessResult(expected))

    def test_tsv(self):
        result = render(P(csv='A\tB\n1\tfoo\n2\tbar'))
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': ['foo', 'bar']
        })
        self.assertEqual(result, ProcessResult(expected))

    def test_no_nan(self):
        # https://www.pivotaltracker.com/story/show/163106728
        result = render(P(csv='A,B\nx,y\nz,NA'))
        expected = pd.DataFrame({
            'A': ['x', 'z'],
            'B': ['y', 'NA'],
        }, dtype='category')
        assert_frame_equal(result.dataframe, expected)
