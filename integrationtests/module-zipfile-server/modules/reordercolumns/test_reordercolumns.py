import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
import reordercolumns


a_table = pd.DataFrame(
    {"name": [1, 2], "date": [2, 3], "count": [3, 4], "float": [4.0, 5.0]}
)


def fake_result(colnames):
    return a_table[colnames]


def render(table, reorder_history):
    params = {"reorder-history": reorder_history}
    return reordercolumns.render(table.copy(), params)


class MigrateParamsTest(unittest.TestCase):
    def test_v0_empty(self):
        self.assertEqual(reordercolumns.migrate_params(""), {"reorder-history": []})

    def test_v0(self):
        self.assertEqual(
            reordercolumns.migrate_params(
                '{"no-param-text":"","reorder-history":[{"column":"FEDERAL_PROGRAMNAME","from":1,"to":0}]}'
            ),
            {
                "reorder-history": [
                    {"column": "FEDERAL_PROGRAMNAME", "from": 1, "to": 0}
                ]
            },
        )

    def test_v1(self):
        self.assertEqual(
            reordercolumns.migrate_params(
                {
                    "no-param-text": "",
                    "reorder-history": [
                        {"column": "FEDERAL_PROGRAMNAME", "from": 1, "to": 0}
                    ],
                }
            ),
            {
                "reorder-history": [
                    {"column": "FEDERAL_PROGRAMNAME", "from": 1, "to": 0}
                ]
            },
        )

    def test_v2(self):
        self.assertEqual(
            reordercolumns.migrate_params(
                {
                    "reorder-history": [
                        {"column": "FEDERAL_PROGRAMNAME", "from": 1, "to": 0}
                    ]
                }
            ),
            {
                "reorder-history": [
                    {"column": "FEDERAL_PROGRAMNAME", "from": 1, "to": 0}
                ]
            },
        )


class ReorderTest(unittest.TestCase):
    def test_reorder_empty(self):
        result = render(a_table, {})
        assert_frame_equal(result, fake_result(["name", "date", "count", "float"]))

    def test_reorder(self):
        # In chronological order, starting with
        # ['name', 'date', 'count', 'float']
        reorder_ops = [
            {
                "column": "count",
                "from": 2,
                "to": 0,
            },  # gives ['count', 'name', 'date', 'float']
            {
                "column": "name",
                "from": 1,
                "to": 2,
            },  # gives ['count', 'date', 'name', 'float']
            {
                "column": "float",
                "from": 3,
                "to": 1,
            },  # gives ['count', 'float', 'date', 'name']
        ]
        result = render(a_table, reorder_ops)
        assert_frame_equal(result, fake_result(["count", "float", "date", "name"]))

    def test_missing_column(self):
        # If an input column is removed (e.g. via select columns)
        # then reorders which refer to it simply do nothing
        reorder_ops = [
            # starts from ['name', 'date', 'count', 'float']
            {
                "column": "count",
                "from": 2,
                "to": 0,
            },  # gives ['count', 'name', 'date', 'float']
            {"column": "nonexistent-name", "from": 4, "to": 1},  # invalid, nop
            {"column": "count", "from": 0, "to": 4},  # invalid, nop
            {
                "column": "float",
                "from": 3,
                "to": 2,
            },  # gives ['count', 'name', 'float', 'date']
        ]
        result = render(a_table, reorder_ops)
        assert_frame_equal(result, fake_result(["count", "name", "float", "date"]))
