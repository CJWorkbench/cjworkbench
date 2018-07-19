from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_nocache
from server.modules.types import ProcessResult
import pandas as pd
import numpy as np
import io
from server.tests.modules.test_refine import MockModule
from server.modules.duplicatecolumnfromtable import DuplicateColumnFromTable

duplicate_column_prefix = 'Copy of'

test_csv = '\n'.join([
    'col_1,col_2,col_3,col_4,{0} col_2'.format(duplicate_column_prefix),
    'Dolores,2018-04-22,3,13.5,some',
    'Bernard,2018-04-23,not_a_count,2.0,more',
    'Ford,2016-10-02,5,9.9,random',
    'Dolores,0_not_a_date,4,2.8,data'
])
reference_table = pd.read_csv(io.StringIO(test_csv), dtype={
    'col_1': object,
    'col_2': object,
    'col_3': object,
    'col_4': np.float64,
    '{0} col_2'.format(duplicate_column_prefix): object
})

def duplicated_column(column_number, table=reference_table.copy()):
    col_to_dup = table.columns[column_number]
    expected_col_name = '{0} {1}'.format(duplicate_column_prefix, col_to_dup)
    table[expected_col_name] = table[col_to_dup]
    return ProcessResult(table)

def duplicated_column_with_existing(column_number, existing_column_number, table=reference_table.copy()):
    col_to_dup = table.columns[column_number]
    existing_column_name = table.columns[existing_column_number]
    expected_col_name = '{0} {1}'.format(existing_column_name, 1)
    table[expected_col_name] = table[col_to_dup]
    return ProcessResult(table)

class DuplicateColumnFromTableTests(LoggedInTestCase):
    # Current dtype choices: "String|Number|Date"
    # Current direction choices: "Select|Ascending|Descending"
    # If the position of the values change, tests will need to be updated

    # NaN and NaT always appear last as the policy in SortFromTable dictates

    def setUp(self):
        super(DuplicateColumnFromTableTests, self).setUp()
        # A reference table for correctness checking
        # Performing date conversion here does not help tests as default test
        # WF does not parse dates
        self.table = reference_table.copy()
        self.workflow = create_testdata_workflow(csv_text=test_csv)
        self.wf_module = load_and_add_module('duplicatecolumnfromtable', workflow=self.workflow)
        self.colnames_pval = get_param_by_id_name('colnames')

    def test_duplicate_column(self):
        # Tests duplicating the first column
        self.colnames_pval.value = 'col_1'
        self.colnames_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, duplicated_column(0))

        # Tests duplicating the third column (second column is special case)
        """self.colnames_pval.value = 'col_3'
        self.colnames_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, duplicated_column(2))

        # Tests duplicating the fourth column
        self.colnames_pval.value = 'col_4'
        self.colnames_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, duplicated_column(3))
        """

    def test_duplicate_with_existing(self):
        # Tests duplicating the second column when an expected column name already exists
        self.colnames_pval.value = 'col_2'
        self.colnames_pval.save()
        result = execute_nocache(self.wf_module)
        self.assertEqual(result, duplicated_column_with_existing(1,4))
