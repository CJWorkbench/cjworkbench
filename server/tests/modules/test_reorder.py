from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_nocache
from server.modules.types import ProcessResult
import json
import pandas as pd
import numpy as np
import io

test_csv = (
    'name,date,count,float\n'
    + 'Dolores,2018-04-22,3,13.5\n'
    + 'Bernard,2018-04-23,not_a_count,2.0\n'
    + 'Ford,2016-10-02,5,\n'
    + 'Dolores,0_not_a_date,4,2.8'
)
# A reference table for correctness checking
reference_table = pd.read_csv(io.StringIO(test_csv), dtype={
    'name': object,
    'date': object,
    'count': object,
    'float': np.float64
})


def reordered_result(colnames):
    return ProcessResult(reference_table[colnames])


class ReorderFromTableTests(LoggedInTestCase):
    # Current dtype choices: "String|Number|Date"
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def setUp(self):
        super(ReorderFromTableTests, self).setUp()
        self.workflow = create_testdata_workflow(csv_text=test_csv)
        self.wf_module = load_and_add_module('reorder', workflow=self.workflow)
        self.history_pval = get_param_by_id_name('reorder-history')

    def test_reorder_empty(self):
        self.history_pval.value = ' '
        self.history_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result,
                         reordered_result(['name', 'date', 'count', 'float']))

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
        self.history_pval.value = json.dumps(reorder_ops)
        self.history_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result,
                         reordered_result(['count', 'float', 'date', 'name']))

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
        self.history_pval.value = json.dumps(reorder_ops)
        self.history_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result,
                         reordered_result(['count', 'name', 'float', 'date']))
