import asyncio
from typing import Any, Dict
import unittest
from unittest.mock import patch
import pandas as pd
from asgiref.sync import async_to_sync
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.modules import joinurl


def P(url='https://app.workbenchdata.com/workflows/2/', colnames='',
      importcols='', type=0, select_columns=False) -> Dict[str, Any]:
    return {
        'url': url,
        'colnames': colnames,
        'importcols': importcols,
        'type': type,
        'select_columns': select_columns,
    }


async def get_workflow_owner():
    return 'owner'  # no need for a User: we mock fetch_external_workflow()


fetch = joinurl.fetch


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(table, params, fetch_result):
    return joinurl.render(table, params, fetch_result=fetch_result)


table = pd.DataFrame([['a', 'b'], ['a', 'c']], columns=['col1', 'key'])

ref_left_join = pd.DataFrame([['a', 'b', 'c', 'd']],
                             columns=['col1', 'key', 'col2', 'col3'])

table_with_types = pd.DataFrame([[1, 2], [1, 3]], columns=['col1', 'key'])
ext_workflow_with_types = pd.DataFrame([[2.0, 3.0, 4.0], [4.0, 1.0, 2.0]],
                                       columns=['key', 'col2', 'col3'])

ref_left_join_with_types = pd.DataFrame(
    [[1, 2.0, 3.0, 4.0]],
    columns=['col1', 'key', 'col2', 'col3']
)


class JoinURLTests(unittest.TestCase):
    def test_no_left(self):
        result = render(pd.DataFrame(), P(), PR('', {'A': [1]}))
        assert_frame_equal(result, pd.DataFrame())

    def test_no_right(self):
        result = render(pd.DataFrame({'A': [1]}), P(), None)
        assert_frame_equal(result, pd.DataFrame({'A': [1]}))

    def test_right_is_error(self):
        result = render(pd.DataFrame({'A': [1]}), P(), PR('error'))
        self.assertEqual(result, 'error')

    def test_join(self):
        # Nothing too technical, do not need to test pandas functions
        result = render(pd.DataFrame({'col1': ['a', 'a'], 'key': ['b', 'c']}),
                        P(type=1, colnames='key'),
                        PR('', {
                            'key': ['b', 'd'],
                            'col2': ['c', 'a'],
                            'col3': ['d', 'b'],
                        }))
        assert_frame_equal(result, pd.DataFrame({
            'col1': ['a'],
            'key': ['b'],
            'col2': ['c'],
            'col3': ['d'],
        }))

    def test_importcols(self):
        result = render(pd.DataFrame({'col1': ['a', 'a'], 'key': ['b', 'c']}),
                        P(type=1, colnames='key', select_columns=True,
                          importcols='col2'),
                        PR('', {
                            'key': ['b', 'd'],
                            'col2': ['c', 'a'],
                            'col3': ['d', 'b'],
                        }))
        self.assertEqual(['col1', 'key', 'col2'],
                         list(result.columns))

    def test_colnames_not_in_right(self):
        result = render(pd.DataFrame({'A': [1], 'B': [2]}),
                        P(colnames='A', select_columns=True,
                          importcols='B'),
                        PR('', {'A': [1], 'C': [2]}))
        self.assertEqual(result, "Selected columns not in target workflow: B")

    def test_cast_int_to_float(self):
        result = render(pd.DataFrame({'A': [1, 2, 3]}),
                        P(type=1, colnames='A'),
                        PR('', {'A': [1.0, 2.0, 4.0]}))
        expected = pd.DataFrame({'A': [1.0, 2.0]})
        assert_frame_equal(result, expected)

    def test_type_mismatch(self):
        result = render(pd.DataFrame({'A': [1, 2, 3]}),
                        P(type=1, colnames='A'),
                        PR('', {'A': ['1', '2', '3']}))
        self.assertEqual(result, (
            'Types do not match for key column "A" (number and text). '
            'Please use a type conversion module '
            'to make these column types consistent.'
        ))

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
