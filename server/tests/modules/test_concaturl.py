import asyncio
import unittest
from unittest.mock import patch
from asgiref.sync import async_to_sync
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.concaturl import ConcatURL
from server.modules.types import ProcessResult
from .util import MockParams


P = MockParams.factory(url='https://app.workbenchdata.com/workflows/2/',
                       source_columns=([], []), type=0)


class MockWfModule:
    def __init__(self, **kwargs):
        self.params = P(**kwargs)

    def get_params(self):
        return self.params


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(params, table, fetch_result):
    result = ConcatURL.render(params, table, fetch_result=fetch_result)
    result.sanitize_in_place()
    return result


async def fetch(wf_module):
    return await ConcatURL.fetch(wf_module)


table = pd.DataFrame({
    'col1': ['a', 'a'],
    'key': ['b', 'c'],
})

ext_workflow = pd.DataFrame({
    'key': ['b', 'd'],
    'col2': ['c', 'a'],
})


class ConcatURLTest(unittest.TestCase):
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
            error='Not a URL'
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

    @patch('server.modules.utils.fetch_external_workflow')
    def test_fetch(self, inner_fetch):
        pr = ProcessResult(pd.DataFrame({'A': [1]}))
        future_pr = asyncio.Future()
        future_pr.set_result(pr)
        inner_fetch.return_value = future_pr

        wf_module = MockWfModule(
            url='https://app.workbenchdata.com/workflows/2/'
        )
        result = async_to_sync(fetch)(wf_module)

        self.assertEqual(result, pr)
        inner_fetch.assert_called_with(wf_module, 2)

    def test_fetch_invalid_url(self):
        wf_module = MockWfModule(
            url='hts:app.workbenchdata.com/workflows/2/'
        )
        result = async_to_sync(fetch)(wf_module)

        self.assertEqual(result, ProcessResult(
            error='Not a valid Workbench workflow URL'
        ))
