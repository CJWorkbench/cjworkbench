import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
from server.modules.concaturl import ConcatURL
from server.modules.types import ProcessResult
from .util import MockParams


P = MockParams.factory(url='https://app.workbenchdata.com/workflows/2/',
                       source_columns=([], []), type=0)


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(params, table, fetch_result):
    result = ConcatURL.render(params, table, fetch_result=fetch_result)
    result.sanitize_in_place()
    return result


table = pd.DataFrame({
    'col1': ['a', 'a'],
    'key': ['b', 'c'],
})

ext_workflow = pd.DataFrame({
    'key': ['b', 'd'],
    'col2': ['c', 'a'],
})


class ConcatURLTests(unittest.TestCase):
    def test_empty(self):
        result = render(P(url=''), pd.DataFrame({'A': [1]}), None)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_empty_right(self):
        result = render(P(), pd.DataFrame({'A': [1]}), ProcessResult())
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'A': [1]}),
            error='The workflow you chose is empty'
        ))

    def test_invalid_url(self):
        result = render(P(url='not a url'), pd.DataFrame({'A': [1]}),
                        ProcessResult(error='Not a URL'))
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'A': [1]}),
            error='The workflow you chose has an error: Not a URL'
        ))

    def test_concat_only_left_columns(self):
        result = render(
            P(type=0, source_columns=False),
            table,
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'col1': ['a', 'a', np.NaN, np.NaN],
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_all_columns(self):
        result = render(
            P(type=1, source_columns=False),
            table,
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_matching_columns(self):
        result = render(
            P(type=2, source_columns=False),
            table,
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'col1': ['a', 'a', np.NaN, np.NaN],
            'key': ['b', 'c', 'b', 'd'],
            'col2': [np.NaN, np.NaN, 'c', 'a'],
        }))

    def test_concat_with_source(self):
        result = render(
            P(type=1, source_columns=True),
            table,
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'Source Workflow': ['Current', 'Current', '2', '2'],
            'key': ['b', 'c', 'b', 'd'],
        }))
