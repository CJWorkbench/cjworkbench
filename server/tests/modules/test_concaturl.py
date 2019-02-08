import asyncio
import unittest
from unittest.mock import patch
from asgiref.sync import async_to_sync
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.modules import concaturl
from .util import MockParams


P = MockParams.factory(url='https://app.workbenchdata.com/workflows/2/',
                       source_columns=([], []), type=0)


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(table, params, fetch_result):
    result = concaturl.render(table, params, fetch_result=fetch_result)
    result.sanitize_in_place()
    return result


async def get_workflow_owner():
    return 'owner'  # no need for a User: we mock fetch_external_workflow()


fetch = concaturl.fetch


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
        result = render(pd.DataFrame({'A': [1]}), P(url=''), None)
        self.assertEqual(result, ProcessResult(pd.DataFrame({'A': [1]})))

    def test_empty_right(self):
        result = render(pd.DataFrame({'A': [1]}), P(), ProcessResult())
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'A': [1]}),
            error='The workflow you chose is empty'
        ))

    def test_invalid_url(self):
        result = render(pd.DataFrame({'A': [1]}), P(url='not a url'),
                        ProcessResult(error='Not a URL'))
        self.assertEqual(result, ProcessResult(
            dataframe=pd.DataFrame({'A': [1]}),
            error='Not a URL'
        ))

    def test_concat_only_left_columns(self):
        result = render(
            table,
            P(type=0, source_columns=False),
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'col1': ['a', 'a', np.NaN, np.NaN],
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_all_columns(self):
        result = render(
            table,
            P(type=1, source_columns=False),
            ProcessResult(ext_workflow)
        )

        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_matching_columns(self):
        result = render(
            table,
            P(type=2, source_columns=False),
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
            table,
            P(type=1, source_columns=True),
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

        params = P(url='https://app.workbenchdata.com/workflows/2/')
        result = async_to_sync(fetch)(params, workflow_id=1,
                                      get_workflow_owner=get_workflow_owner)

        self.assertEqual(result, pr)
        inner_fetch.assert_called_with(1, 'owner',  2)

    def test_fetch_invalid_url(self):
        params = P(url='hts:app.workbenchdata.com/workflows/2/')
        result = async_to_sync(fetch)(params, workflow_id=1,
                                      get_workflow_owner=get_workflow_owner)

        self.assertEqual(result, ProcessResult(
            error='Not a valid Workbench workflow URL'
        ))
