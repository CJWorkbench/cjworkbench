import asyncio
from typing import Any, Dict
import unittest
from unittest.mock import patch
import pandas as pd
from asgiref.sync import async_to_sync
from pandas.testing import assert_frame_equal
from server.modules.joinurl import JoinURL, _join_type_map
from server.modules.types import ProcessResult


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


fetch = JoinURL.fetch


def PR(error, *args, **kwargs):
    """Shortcut ProcessResult builder."""
    return ProcessResult(pd.DataFrame(*args, **kwargs), error)


def render(params, table, fetch_result):
    return JoinURL.render(params, table, fetch_result=fetch_result)


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
        result = render(P(), pd.DataFrame(), PR('', {'A': [1]}))
        self.assertEqual(result, ProcessResult())

    def test_no_right(self):
        result = render(P(), pd.DataFrame({'A': [1]}), None)
        self.assertEqual(result, ProcessResult())

    def test_right_is_error(self):
        result = render(P(), pd.DataFrame({'A': [1]}), PR('error'))
        self.assertEqual(result, ProcessResult(error='error'))

    def test_join(self):
        # Nothing too technical, do not need to test pandas functions
        result = render(P(type=_join_type_map.index('inner'),
                          colnames='key'),
                        pd.DataFrame({'col1': ['a', 'a'], 'key': ['b', 'c']}),
                        PR('', {
                            'key': ['b', 'd'],
                            'col2': ['c', 'a'],
                            'col3': ['d', 'b'],
                        }))
        assert_frame_equal(result.dataframe, pd.DataFrame({
            'col1': ['a'],
            'key': ['b'],
            'col2': ['c'],
            'col3': ['d'],
        }))

    def test_importcols(self):
        result = render(P(type=_join_type_map.index('inner'),
                          colnames='key', select_columns=True,
                          importcols='col2'),
                        pd.DataFrame({'col1': ['a', 'a'], 'key': ['b', 'c']}),
                        PR('', {
                            'key': ['b', 'd'],
                            'col2': ['c', 'a'],
                            'col3': ['d', 'b'],
                        }))
        self.assertEqual(['col1', 'key', 'col2'],
                         list(result.dataframe.columns))

    def test_colnames_not_in_right(self):
        result = render(P(colnames='A', select_columns=True,
                          importcols='B'),
                        pd.DataFrame({'A': [1], 'B': [2]}),
                        PR('', {'A': [1], 'C': [2]}))
        self.assertEqual(result, ProcessResult(error=(
            "Selected columns not in target workflow: B"
        )))

    def test_cast_int_to_float(self):
        result = render(P(type=_join_type_map.index('inner'),
                          colnames='A'),
                        pd.DataFrame({'A': [1, 2, 3]}),
                        PR('', {'A': [1.0, 2.0, 4.0]}))
        expected = pd.DataFrame({'A': [1.0, 2.0]})
        assert_frame_equal(result.dataframe, expected)

    def test_type_mismatch(self):
        result = render(P(type=_join_type_map.index('inner'),
                          colnames='A'),
                        pd.DataFrame({'A': [1, 2, 3]}),
                        PR('', {'A': ['1', '2', '3']}))
        self.assertEqual(result, ProcessResult(error=(
            'Types do not match for key column "A" (number and text). '
            'Please use a type conversion module '
            'to make these column types consistent.'
        )))

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
