from server.tests.utils import *
from server.execute import execute_nocache
import json
import pandas as pd
import numpy as np
import io


class RenameFromTableTests(LoggedInTestCase):

    def setUp(self):
        super(RenameFromTableTests, self).setUp()
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
        self.wf_module = load_and_add_module('rename', workflow=self.workflow)
        self.entries_pval = get_param_by_id_name('rename-entries')

    def test_rename_empty(self):
        # Should only happen when a module is first created, returns table
        self.entries_pval.value = ' '
        self.entries_pval.save()
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

    def test_rename(self):
        self.entries_pval.value = json.dumps({
            'name': 'name1',
            'count': 'CNT'
        })
        self.entries_pval.save()
        out = execute_nocache(self.wf_module)
        ref = self.table.copy()
        ref.columns = ['name1', 'date', 'CNT', 'float']
        self.assertTrue(out.equals(ref))