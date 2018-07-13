import io
import json
import pandas as pd
from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_nocache
from server.modules.refine import Refine
from server.modules.types import ProcessResult


test_csv = '\n'.join([
    'name,date,count',
    'Dolores,1524355200000,3',
    'Bernard,1524355200000,5',
    'Ford,1475366400000,5',
    'Dolores,1475366400000,4',
])
reference_table = pd.read_csv(io.StringIO(test_csv))


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
        if name in self.params:
            return self.params[name]
        return ''

    def get_param_menu_idx(self, name):
        if name in self.params:
            return self.params[name]
        return ''


class RefineTests(LoggedInTestCase):
    def setUp(self):
        super(RefineTests, self).setUp()
        self.workflow = create_testdata_workflow(csv_text=test_csv)
        self.wf_module = load_and_add_module('refine', workflow=self.workflow)
        self.edits_pval = get_param_by_id_name('refine')
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
        result = execute_nocache(self.wf_module)
        expected_table = reference_table[[False, True, True, False]]
        # reset to contiguous indices
        expected_table.index = pd.RangeIndex(len(expected_table.index))
        self.assertEqual(result, ProcessResult(expected_table))

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
        result = execute_nocache(self.wf_module)
        expected_table = reference_table[[True, True, True, True]]
        self.assertEqual(result, ProcessResult(expected_table))

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
        result = execute_nocache(self.wf_module)
        expected_table = reference_table.copy()
        expected_table \
            .loc[expected_table['name'] == 'Dolores', 'name'] = 'Wyatt'
        self.assertEqual(result, ProcessResult(expected_table))

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
        result = execute_nocache(self.wf_module)
        expected_table = reference_table.copy()
        expected_table.loc[expected_table['count'] == 5, 'count'] = 4
        self.assertEqual(result, ProcessResult(expected_table))

    def test_render_date(self):
        # Since we don't have a upstream module that can feed dates with
        # minimal fuss we will directly test Refine's render() function here.
        dates_table = reference_table.copy()
        dates_table['date'] = pd.to_datetime(dates_table['date'], unit='ms')

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
            'refine': json.dumps(self.edits)
        })
        result = Refine.render(mock_refine, dates_table.copy())
        expected_table = dates_table.copy()
        expected_table \
            .loc[expected_table['date'] == pd.Timestamp('2016-10-02 00:00:00'),
                 'date'] = pd.Timestamp('2016-12-04 00:00:00')
        self.assertEqual(result, ProcessResult(expected_table))

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
            'refine': json.dumps(self.edits)
        })
        result = Refine.render(mock_refine, dates_table.copy())
        expected_table = dates_table[[True, True, False, False]]
        self.assertEqual(result, ProcessResult(expected_table))
