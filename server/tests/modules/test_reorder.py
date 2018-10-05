import json
import unittest
import pandas as pd
from server.modules.reorder import ReorderFromTable
from server.modules.types import ProcessResult
from .util import MockParams


a_table = pd.DataFrame({
    'name': [1, 2],
    'date': [2, 3],
    'count': [3, 4],
    'float': [4.0, 5.0],
})


class MockWfModule:
    def __init__(self, reorder_history_json: str):
        self.reorder_history = reorder_history_json

    def get_param_raw(self, key, _unused):
        return getattr(self, key.replace('-', '_'))


def fake_result(colnames):
    return ProcessResult(a_table[colnames])


def render(reorder_history, table):
    params = MockParams(reorder_history=reorder_history)
    result = ReorderFromTable.render(params, table.copy())
    return ProcessResult.coerce(result)


class ReorderTest(unittest.TestCase):
    def test_reorder_empty(self):
        result = render({}, a_table)
        self.assertEqual(result,
                         fake_result(['name', 'date', 'count', 'float']))

    def test_reorder(self):
        # In chronological order, starting with
        # ['name', 'date', 'count', 'float']
        reorder_ops = [
            {
                'column': 'count',
                'from': 2,
                'to': 0
            },  # gives ['count', 'name', 'date', 'float']
            {
                'column': 'name',
                'from': 1,
                'to': 2
            },  # gives ['count', 'date', 'name', 'float']
            {
                'column': 'float',
                'from': 3,
                'to': 1
            },  # gives ['count', 'float', 'date', 'name']
        ]
        result = render(reorder_ops, a_table)
        self.assertEqual(result,
                         fake_result(['count', 'float', 'date', 'name']))

    def test_missing_column(self):
        # If an input column is removed (e.g. via select columns)
        # then reorders which refer to it simply do nothing
        reorder_ops = [
            # starts from ['name', 'date', 'count', 'float']
            {
                'column': 'count',
                'from': 2,
                'to': 0
            },  # gives ['count', 'name', 'date', 'float']
            {
                'column': 'nonexistent-name',
                'from': 4,
                'to': 1
            },  # invalid, nop
            {
                'column': 'count',
                'from': 0,
                'to': 4
            },  # invalid, nop
            {
                'column': 'float',
                'from': 3,
                'to': 2
            },  # gives ['count', 'name', 'float', 'date']
        ]
        result = render(reorder_ops, a_table)
        self.assertEqual(result,
                         fake_result(['count', 'name', 'float', 'date']))
