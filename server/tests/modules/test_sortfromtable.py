from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_nocache
from server.modules.types import ProcessResult
import pandas as pd
import numpy as np
import io
from server.modules.sortfromtable import SortFromTable


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


test_csv = '\n'.join([
    'name,date,count,float'
    'Dolores,2018-04-22,3,13.5'
    'Bernard,2018-04-23,not_a_count,2.0'
    'Ford,2016-10-02,5,'
    'Dolores,0_not_a_date,4,2.8'
])
reference_table = pd.read_csv(io.StringIO(test_csv), dtype={
    'name': object,
    'date': object,
    'count': object,
    'float': np.float64
})


def ordered_result(row_numbers, table=reference_table):
    pieces = [table[i:i+1] for i in row_numbers]
    return ProcessResult(pd.concat(pieces))


class SortFromTableTests(LoggedInTestCase):
    # Current dtype choices: "String|Number|Date"
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def setUp(self):
        super(SortFromTableTests, self).setUp()
        # A reference table for correctness checking
        # Performing date conversion here does not help tests as default test
        # WF does not parse dates
        self.table = reference_table.copy()
        self.dates_table = self.table.copy()
        self.dates_table['date'] = pd.to_datetime(self.dates_table['date'],
                                                  errors="coerce")
        self.workflow = create_testdata_workflow(csv_text=test_csv)
        self.wf_module = load_and_add_module('sort', workflow=self.workflow)
        self.column_pval = get_param_by_id_name('column')
        self.dtype_pval = get_param_by_id_name('dtype')
        self.direction_pval = get_param_by_id_name('direction')

    def test_str_ordering(self):
        # Tests ordering of a string column as strings
        self.column_pval.value = 'name'
        self.column_pval.save()
        # dtype is string
        self.dtype_pval.value = 0
        self.dtype_pval.save()

        # If direction is "Select", NOP
        self.direction_pval.value = 0
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 1, 2, 3]))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([1, 0, 3, 2]))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([2, 0, 3, 1]))

        # Tests ordering of a numeric column as strings
        self.column_pval.value = 'float'
        self.column_pval.save()
        # dtype is string
        self.dtype_pval.value = 0
        self.dtype_pval.save()
        # We only test Ascending here; others have been covered above
        self.direction_pval.value = 1
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 1, 3, 2]))

        # Test ordering of a date column as string,
        # using SortFromTable's render() directly
        mock_sort = MockModule({
            'column': 'date',
            'dtype': 0,
            # We only test Ascending here; others have been covered above
            'direction': 1
        })
        result = SortFromTable.render(mock_sort, self.dates_table.copy())
        self.assertEqual(result,
                         ordered_result([2, 0, 1, 3], self.dates_table))

    def test_numeric_ordering(self):
        # Test ordering of a numeric column as numeric
        self.column_pval.value = 'float'
        self.column_pval.save()
        # dtype is number
        self.dtype_pval.value = 1
        self.dtype_pval.save()

        # If direction is "Select", NOP
        self.direction_pval.value = 0
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 1, 2, 3]))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([1, 3, 0, 2]))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 3, 1, 2]))

        # Test ordering of a string column as numeric
        self.column_pval.value = 'count'
        self.column_pval.save()
        # dtype is number
        self.dtype_pval.value = 1
        self.dtype_pval.save()
        # We only test Ascending here; others have been covered above
        self.direction_pval.value = 1
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 3, 2, 1]))

    def test_date_ordering(self):
        # Test ordering of a string column as date
        self.column_pval.value = 'date'
        self.column_pval.save()
        # dtype is date
        self.dtype_pval.value = 2
        self.dtype_pval.save()

        # If direction is "Select", NOP
        self.direction_pval.value = 0
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([0, 1, 2, 3]))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([2, 0, 1, 3]))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, ordered_result([1, 0, 2, 3]))

        # Test ordering of a date column as date,
        # using SortFromTable's render() directly
        mock_sort = MockModule({
            'column': 'date',
            'dtype': 2,
            # We only test Ascending here; others have been covered above
            'direction': 1
        })
        result = SortFromTable.render(mock_sort, self.dates_table.copy())
        self.assertEqual(result,
                         ordered_result([2, 0, 1, 3], self.dates_table))
