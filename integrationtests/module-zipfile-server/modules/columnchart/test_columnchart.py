#!/usr/bin/env python3

from collections import namedtuple
import unittest
import numpy as np
import pandas as pd
from columnchart import render, migrate_params


DefaultParams = {
    'title': '',
    'x_axis_label': '',
    'y_axis_label': '',
    'x_column': '',
    'y_columns': [],
}


Column = namedtuple('Column', ('name', 'type', 'format'))


def P(**kwargs):
    """Easily build params, falling back to defaults."""
    assert not (set(kwargs.keys()) - set(DefaultParams.keys()))
    return {
        **DefaultParams,
        **kwargs,
    }


class MigrateParamsTest(unittest.TestCase):
    def test_v0_empty_y_columns(self):
        result = migrate_params({
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': '',
        })
        self.assertEqual(result, {
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': [],
        })

    def test_v0_json_parse(self):
        result = migrate_params({
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': '[{"column": "X", "color": "#111111"}]',
        })
        self.assertEqual(result, {
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': [{'column': 'X', 'color': '#111111'}],
        })

    def test_v1_no_op(self):
        result = migrate_params({
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': [{'column': 'X', 'color': '#111111'}],
        })
        self.assertEqual(result, {
            'title': 'Title',
            'x_axis_label': 'X axis',
            'y_axis_label': 'Y axis',
            'x_column': 'X',
            'y_columns': [{'column': 'X', 'color': '#111111'}],
        })


class IntegrationTest(unittest.TestCase):
    maxDiff = None

    def test_happy_path(self):
        dataframe, error, json_dict = render(
            pd.DataFrame({
                'A': ['foo', 'bar'],
                'B': [1, 2],
                'C': [2, 3],
            }),
            P(
                x_column='A',
                y_columns=[
                    {'column': 'B', 'color': '#bbbbbb'},
                    {'column': 'C', 'color': '#cccccc'},
                ]
            ),
            input_columns={
                'A': Column('A', 'text', None),
                'B': Column('B', 'number', '{:,}'),
                'C': Column('C', 'number', '{:,f}'),
            }
        )
        # Check values
        self.assertEqual(json_dict['data'][0]['values'], [
            {'bar': 'B', 'y': 1, 'group': 0},
            {'bar': 'C', 'y': 2, 'group': 0},
            {'bar': 'B', 'y': 2, 'group': 1},
            {'bar': 'C', 'y': 3, 'group': 1},
        ])
        # Check axis format is first Y column's format
        self.assertEqual(json_dict['axes'][1]['format'], ',r')

    def test_output_nulls(self):
        dataframe, error, json_dict = render(
            pd.DataFrame({
                'A': ['foo', 'bar', None],
                'B': [np.nan, 2, 3],
                'C': [2, 3, 4],
            }),
            P(
                x_column='A',
                y_columns=[
                    {'column': 'B', 'color': '#bbbbbb'},
                    {'column': 'C', 'color': '#cccccc'},
                ]
            ),
            input_columns={
                'A': Column('A', 'text', None),
                'B': Column('B', 'number', '{:,}'),
                'C': Column('C', 'number', '{:,f}'),
            }
        )
        # Check values
        self.assertEqual(json_dict['data'][0]['values'], [
            {'bar': 'B', 'y': None, 'group': 0},
            {'bar': 'C', 'y': 2.0, 'group': 0},
            {'bar': 'B', 'y': 2.0, 'group': 1},
            {'bar': 'C', 'y': 3.0, 'group': 1},
            {'bar': 'B', 'y': 3.0, 'group': 2},
            {'bar': 'C', 'y': 4.0, 'group': 2},
        ])
        # Check axis format is first Y column's format
        self.assertEqual(json_dict['axes'][1]['format'], ',r')


if __name__ == '__main__':
    unittest.main()
