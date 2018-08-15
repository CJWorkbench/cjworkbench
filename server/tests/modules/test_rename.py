import io
import json
import numpy as np
import pandas as pd
from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_wfmodule
from server.modules.types import ProcessResult

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


class RenameFromTableTests(LoggedInTestCase):

    def setUp(self):
        super(RenameFromTableTests, self).setUp()
        self.workflow = create_testdata_workflow(csv_text=test_csv)
        self.wf_module = load_and_add_module('rename', workflow=self.workflow)
        self.entries_pval = get_param_by_id_name('rename-entries')

    def test_rename_empty_str(self):
        # Should only happen when a module is first created. Return table
        self.entries_pval.value = ' '
        self.entries_pval.save()
        result = execute_wfmodule(self.wf_module)
        self.assertEqual(result, ProcessResult(reference_table))

    def test_rename_empty(self):
        # If there are no entries, return table
        self.entries_pval.value = json.dumps({})
        self.entries_pval.save()
        result = execute_wfmodule(self.wf_module)
        self.assertEqual(result, ProcessResult(reference_table))

    def test_rename(self):
        self.entries_pval.value = json.dumps({
            'name': 'name1',
            'count': 'CNT'
        })
        self.entries_pval.save()
        result = execute_wfmodule(self.wf_module)
        expected_table = reference_table.copy()
        expected_table.columns = ['name1', 'date', 'CNT', 'float']
        self.assertEqual(result, ProcessResult(expected_table))
