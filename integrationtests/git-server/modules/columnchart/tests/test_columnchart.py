#!/usr/bin/env python3

import unittest
import pandas as pd
from columnchart import render, migrate_params


DefaultParams = {
    'title': '',
    'x_axis_label': '',
    'y_axis_label': '',
    'x_column': '',
    'y_columns': [],
}


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
    def test_happy_path(self):
        dataframe, error, json_dict = render(pd.DataFrame({
            'A': ['foo', 'bar'],
            'B': [1, 2],
            'C': [2, 3],
        }), P(
            x_column='A',
            y_columns=[
                {'column': 'B', 'color': '#bbbbbb'},
                {'column': 'C', 'color': '#cccccc'},
            ]
        ))
        self.assertEqual(json_dict['data'][0]['values'], [
            {'bar': 'B', 'y': 1, 'group': 0, 'name': 'foo'},
            {'bar': 'B', 'y': 2, 'group': 1, 'name': 'bar'},
            {'bar': 'C', 'y': 2, 'group': 0, 'name': 'foo'},
            {'bar': 'C', 'y': 3, 'group': 1, 'name': 'bar'},
        ])
