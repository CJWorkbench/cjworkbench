from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_nocache
import json
import pandas as pd
import io
from server.modules.refine import Refine


class MockModule:
    # A mock module that stores parameter data,
    # for directly testing a module's render() function
    # We can move this into test utils if it's more widely applicable

    def __init__(self, params):
        self.params = params

    def get_param_raw(self, name, ptype):
        if name in self.params:
            return self.params[name]
        return ''

    def get_param_column(self, name):
        if 'column' in self.params:
            return self.params['column']
        return ''


class RefineTests(LoggedInTestCase):
    def setUp(self):
        super(RefineTests, self).setUp()
        self.test_csv = 'name,date,count\nDolores,1524355200000,3\nBernard,1524355200000,5\nFord,1475366400000,5\nDolores,1475366400000,4'
        # A reference table for correctness checking
        # Performing date conversion here does not help tests as default test WF does not parse dates
        # self.table = pd.read_csv(io.StringIO(self.test_csv), parse_dates=['date'])
        self.table = pd.read_csv(io.StringIO(self.test_csv))
        self.workflow = create_testdata_workflow(csv_text=self.test_csv)
        self.wf_module = load_and_add_module('refine', workflow=self.workflow)
        self.edits_pval = get_param_by_id_name('edits')
        self.column_pval = get_param_by_id_name('column')
        self.edits = []

    def test_render_select(self):
        # Perform a deselection
        self.column_pval.value = 'name'
        self.column_pval.save()
        self.edits.append({
            'type': 'select',
            'column': 'name',
            'content': {
                'value': 'Dolores'
            }
        })
        self.edits_pval.value = json.dumps(self.edits)
        self.edits_pval.save()
        out = execute_nocache(self.wf_module)
        ref_table = self.table[[False, True, True, False]]
        self.assertTrue(out.equals(ref_table))

        # Perform a selection on the same value, table should be back to normal
        self.edits.append({
            'type': 'select',
            'column': 'name',
            'content': {
                'value': 'Dolores'
            }
        })
        self.edits_pval.value = json.dumps(self.edits)
        self.edits_pval.save()
        out = execute_nocache(self.wf_module)
        ref_table = self.table[[True, True, True, True]]
        self.assertTrue(out.equals(ref_table))

    def test_render_edit(self):
        # Perform a single edit on a string
        self.column_pval.value = 'name'
        self.column_pval.save()
        self.edits.append({
            'type': 'change',
            'column': 'name',
            'content': {
                'fromVal': 'Dolores',
                'toVal': 'Wyatt'
            }
        })
        self.edits_pval.value = json.dumps(self.edits)
        self.edits_pval.save()
        out = execute_nocache(self.wf_module)
        ref_table = self.table.copy()
        ref_table.loc[ref_table['name'] == 'Dolores', 'name'] = 'Wyatt'
        self.assertTrue(out.equals(ref_table))

        # Perform a single edit on a number
        self.column_pval.value = 'count'
        self.column_pval.save()
        # Content are all strings as this is what we get from UI
        self.edits = [{
            'type': 'change',
            'column': 'count',
            'content': {
                'fromVal': '5',
                'toVal': '4'
            }
        }]
        self.edits_pval.value = json.dumps(self.edits)
        self.edits_pval.save()
        out = execute_nocache(self.wf_module)
        ref_table = self.table.copy()
        ref_table.loc[ref_table['count'] == 5, 'count'] = 4
        self.assertTrue(out.equals(ref_table))

    def test_render_date(self):
        # Since we don't have a upstream module that can feed dates with minimal fuss
        # we will directly test Refine's render() function here.
        dates_table = pd.read_csv(io.StringIO(self.test_csv))
        dates_table['date'] = pd.to_datetime(dates_table['date'], unit='ms')
        print(dates_table.dtypes)

        # Perform a single edit on a date
        self.edits = [{
            'type': 'change',
            'column': 'date',
            'content': {
                'fromVal': '2016-10-02 00:00:00',
                'toVal': '2016-12-04 00:00:00'
            }
        }]
        mock_refine = MockModule({
            'column': 'date',
            'edits': json.dumps(self.edits)
        })
        out = Refine.render(mock_refine, dates_table.copy())

        # Perform a single selection on a date
        self.edits = [{
            'type': 'select',
            'column': 'date',
            'content': {
                'value': '2016-10-02',
            }
        }]
        mock_refine = MockModule({
            'column': 'date',
            'edits': json.dumps(self.edits)
        })
        out = Refine.render(mock_refine, dates_table.copy())