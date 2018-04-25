from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_nocache
import json
import pandas as pd
import numpy as np
import io
from server.tests.modules.test_refine import MockModule
from server.modules.sortfromtable import SortFromTable


def reorder_table(table, order):
    # Reorders a table for the given "correct" order
    ret_table = pd.DataFrame(columns=table.columns)
    for o in order:
        ret_table = ret_table.append(table.iloc[[o]])
    for col in table.columns:
        ret_table[col] = ret_table[col].astype(table[col].dtype)
    return ret_table.reset_index()


class SortFromTableTests(LoggedInTestCase):
    # Current dtype choices: "String|Number|Date"
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def setUp(self):
        super(SortFromTableTests, self).setUp()
        self.test_csv = (
            'name,date,count,float\n'
            + 'Dolores,2018-04-22,3,13.5\n'
            + 'Bernard,2018-04-23,not_a_count,2.0\n'
            + 'Ford,2016-10-02,5,\n'
            + 'Dolores,0_not_a_date,4,2.8'
        )
        # A reference table for correctness checking
        # Performing date conversion here does not help tests as default test WF does not parse dates
        # self.table = pd.read_csv(io.StringIO(self.test_csv), parse_dates=['date'])
        self.table = pd.read_csv(io.StringIO(self.test_csv), dtype={
            'name': object,
            'date': object,
            'count': object,
            'float': np.float64
        })
        self.dates_table = self.table.copy()
        self.dates_table['date'] = pd.to_datetime(self.dates_table['date'], errors="coerce")
        self.workflow = create_testdata_workflow(csv_text=self.test_csv)
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
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [1, 0, 3, 2]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [2, 0, 3, 1]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # Tests ordering of a numeric column as strings
        self.column_pval.value = 'float'
        self.column_pval.save()
        # dtype is string
        self.dtype_pval.value = 0
        self.dtype_pval.save()
        # We only test Ascending here; others have been covered above
        self.direction_pval.value = 1
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [0, 1, 3, 2]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # Test ordering of a date column as string,
        # using SortFromTable's render() directly
        mock_sort = MockModule({
            'column': 'date',
            'dtype': 0,
            # We only test Ascending here; others have been covered above
            'direction': 1
        })
        out = SortFromTable.render(mock_sort, self.dates_table.copy())
        ref_order = [2, 0, 1, 3]
        ref_table = reorder_table(self.dates_table, ref_order)
        self.assertTrue(out.equals(ref_table))


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
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [1, 3, 0, 2]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [0, 3, 1, 2]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # Test ordering of a string column as numeric
        self.column_pval.value = 'count'
        self.column_pval.save()
        # dtype is number
        self.dtype_pval.value = 1
        self.dtype_pval.save()
        # We only test Ascending here; others have been covered above
        self.direction_pval.value = 1
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [0, 3, 2, 1]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))


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
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

        # If direction is "Ascending"
        self.direction_pval.value = 1
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [2, 0, 1, 3]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # If direction is "Descending"
        self.direction_pval.value = 2
        self.direction_pval.save()
        out = execute_nocache(self.wf_module)
        ref_order = [1, 0, 2, 3]
        ref_table = reorder_table(self.table, ref_order)
        self.assertTrue(out.equals(ref_table))

        # Test ordering of a date column as date,
        # using SortFromTable's render() directly
        mock_sort = MockModule({
            'column': 'date',
            'dtype': 2,
            # We only test Ascending here; others have been covered above
            'direction': 1
        })
        out = SortFromTable.render(mock_sort, self.dates_table.copy())
        ref_order = [2, 0, 1, 3]
        ref_table = reorder_table(self.dates_table, ref_order)
        self.assertTrue(out.equals(ref_table))