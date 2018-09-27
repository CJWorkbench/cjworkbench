import unittest
import pandas as pd
from server.modules.pastecsv import PasteCSV
from server.modules.types import ProcessResult


class MockWfModule:
    def __init__(self, csv='', has_header_row=True):
        self.csv = csv
        self.has_header_row = has_header_row

    def get_param_string(self, _):
        return self.csv

    def get_param_checkbox(self, _):
        return self.has_header_row


def render(*args, **kwargs):
    wf_module = MockWfModule(*args, **kwargs)
    result = PasteCSV.render(wf_module, pd.DataFrame())
    result = ProcessResult.coerce(result)
    return result


class PasteCSVTests(unittest.TestCase):
    def test_empty(self):
        result = render('', True)
        self.assertEqual(result, ProcessResult())

    def test_csv(self):
        result = render('A,B\n1,foo\n2,bar')
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': ['foo', 'bar']
        })
        self.assertEqual(result, ProcessResult(expected))

    def test_tsv(self):
        result = render('A\tB\n1\tfoo\n2\tbar')
        expected = pd.DataFrame({
            'A': [1, 2],
            'B': ['foo', 'bar']
        })
        self.assertEqual(result, ProcessResult(expected))
