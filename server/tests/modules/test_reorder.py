from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_nocache
import json
import pandas as pd
import numpy as np
import io
from server.modules.reorder import ReorderFromTable


class ReorderFromTableTests(LoggedInTestCase):
    # Current dtype choices: "String|Number|Date"
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def setUp(self):
        super(ReorderFromTableTests, self).setUp()
        self.test_csv = (
            'name,date,count,float\n'
            + 'Dolores,2018-04-22,3,13.5\n'
            + 'Bernard,2018-04-23,not_a_count,2.0\n'
            + 'Ford,2016-10-02,5,\n'
            + 'Dolores,0_not_a_date,4,2.8'
        )
        # A reference table for correctness checking
        self.table = pd.read_csv(io.StringIO(self.test_csv), dtype={
            'name': object,
            'date': object,
            'count': object,
            'float': np.float64
        })
        self.workflow = create_testdata_workflow(csv_text=self.test_csv)
        self.wf_module = load_and_add_module('reorder', workflow=self.workflow)
        self.history_pval = get_param_by_id_name('reorder-history')

    def test_reorder_empty(self):
        self.history_pval.value = ' '
        self.history_pval.save()
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

    def test_reorder(self):
        # In chronological order
        reorder_ops = [
            {
                'column': 'count',
                'from': 2,
                'to': 0
            },  # gives ['count', 'name', 'date', 'float']
            {
                'column': 'name',
                'from': 1,
                'to': 3
            },  # gives ['count', 'date', 'name', 'float']
            {
                'column': 'float',
                'from': 3,
                'to': 2
            },  # gives ['count', 'date', 'float', 'name']
        ]
        self.history_pval.value = json.dumps(reorder_ops)
        self.history_pval.save()
        out = execute_nocache(self.wf_module)
        ref_cols = ['count', 'date', 'float', 'name']
        self.assertEqual(out.columns.tolist(), ref_cols)
        for col in ref_cols:
            self.assertTrue(out[col].equals(self.table[col]))
