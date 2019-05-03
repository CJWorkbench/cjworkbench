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
                       add_source_column=False, columns_from='input')


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(table, params, fetch_result):
    return concaturl.render(table, params, fetch_result=fetch_result)


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
        assert_frame_equal(result, pd.DataFrame({'A': [1]}))

    def test_empty_right(self):
        result = render(pd.DataFrame({'A': [1]}), P(), ProcessResult())
        self.assertEqual(result, 'The workflow you chose is empty')

    def test_invalid_url(self):
        result = render(pd.DataFrame({'A': [1]}), P(url='not a url'),
                        ProcessResult(error='Not a URL'))
        self.assertEqual(result, 'Not a URL')

    def test_concat_only_left_columns(self):
        result = render(
            table,
            P(columns_from='input', add_source_column=False),
            ProcessResult(ext_workflow)
        )
        assert_frame_equal(result, pd.DataFrame({
            'col1': ['a', 'a', np.NaN, np.NaN],
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_intersect_columns(self):
        result = render(
            table,
            P(columns_from='intersection', add_source_column=False),
            ProcessResult(ext_workflow)
        )
        assert_frame_equal(result, pd.DataFrame({
            'key': ['b', 'c', 'b', 'd'],
        }))

    def test_concat_union_columns(self):
        result = render(
            table,
            P(columns_from='union', add_source_column=False),
            ProcessResult(ext_workflow)
        )
        assert_frame_equal(result, pd.DataFrame({
            'col1': ['a', 'a', np.NaN, np.NaN],
            'key': ['b', 'c', 'b', 'd'],
            'col2': [np.NaN, np.NaN, 'c', 'a'],
        }))

    def test_concat_with_source(self):
        result = render(
            table,
            P(columns_from='intersection', add_source_column=True),
            ProcessResult(ext_workflow)
        )
        assert_frame_equal(result, pd.DataFrame({
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


class MigrateParamsTest(unittest.TestCase):
    def test_v0(self):
        self.assertEqual(concaturl.migrate_params({
            'url': 'https://app.workbenchdata.com/workflows/123',
            'type': 2,
            'source_columns': False,
            'version_select': ''
        }), {
            'url': 'https://app.workbenchdata.com/workflows/123',
            'columns_from': 'union',
            'add_source_column': False,
            'version_select': ''
        })

    def test_v1(self):
        self.assertEqual(concaturl.migrate_params({
            'url': 'https://app.workbenchdata.com/workflows/123',
            'columns_from': 'intersection',
            'add_source_column': False,
            'version_select': ''
        }), {
            'url': 'https://app.workbenchdata.com/workflows/123',
            'columns_from': 'intersection',
            'add_source_column': False,
            'version_select': ''
        })
