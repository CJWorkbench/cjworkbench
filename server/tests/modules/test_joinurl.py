import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
from server.modules.joinurl import JoinURL, _join_type_map
from server.modules.types import ProcessResult
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        add_new_workflow, set_string, \
        set_integer, get_param_by_id_name

class JoinURLTests(LoggedInTestCase):
    def setUp(self):
        super(JoinURLTests, self).setUp()  # log in
        self.wfm = load_and_add_module('joinurl')
        self.url_pval = get_param_by_id_name('url')
        self.colnames_pval = get_param_by_id_name('colnames')
        self.importcols_pval = get_param_by_id_name('importcols')
        self.type_pval = get_param_by_id_name('type')

        self.valid_workflow_URL = 'https://app.workbenchdata.com/workflows/2/'

        self.table = pd.DataFrame([['a', 'b'], ['a', 'c']], columns=['col1', 'key'])
        self.ext_workflow = pd.DataFrame([['b', 'c', 'd'], ['d', 'a', 'b']], columns=['key', 'col2', 'col3'])

        self.ref_left_join = pd.DataFrame([['a', 'b', 'c', 'd']],
                                             columns=['col1', 'key', 'col2', 'col3'])

        self.table_with_types = pd.DataFrame([[1, 2], [1, 3]], columns=['col1', 'key'])
        self.ext_workflow_with_types = pd.DataFrame([[2.0, 3.0, 4.0], [4.0, 1.0, 2.0]], columns=['key', 'col2', 'col3'])

        self.ref_left_join_with_types = pd.DataFrame([[1, 2.0, 3.0, 4.0]],
                                             columns=['col1', 'key', 'col2', 'col3'])

        version = self.wfm.store_fetched_table(self.ext_workflow)
        self.wfm.set_fetched_data_version(version)

    def test_first_applied(self):
        # no upload state
        version = self.wfm.store_fetched_table(None)
        self.wfm.set_fetched_data_version(version)
        result = JoinURL.render(self.wfm, None)
        self.assertEqual(result, ProcessResult())

        # Upload state but empty datagrid
        version = self.wfm.store_fetched_table(self.table)
        self.wfm.set_fetched_data_version(version)
        result = JoinURL.render(self.wfm, None)
        self.assertEqual(result, ProcessResult())

    def test_join(self):
        # Nothing too technical, do not need to test pandas functions
        set_string(self.url_pval, self.valid_workflow_URL)
        set_string(self.colnames_pval, 'key')

        set_integer(self.type_pval, _join_type_map.index("inner"))
        result = JoinURL.render(self.wfm, self.table)
        assert_frame_equal(self.ref_left_join, result.dataframe)

    def test_importcols(self):
        # Should only import 1 column
        set_string(self.url_pval, self.valid_workflow_URL)
        set_string(self.colnames_pval, 'key')
        set_string(self.importcols_pval, 'col2')

        set_integer(self.type_pval, _join_type_map.index("inner"))
        result = JoinURL.render(self.wfm, self.table)
        assert_frame_equal(self.ref_left_join[['col1', 'key', 'col2']], result.dataframe)

    def test_columns_no_exist(self):
        # Should throw error for select column not existing
        set_string(self.importcols_pval, 'non_existent_col')
        set_string(self.colnames_pval, 'key')
        result = JoinURL.render(self.wfm, self.table)
        self.assertEqual("Import columns not in target workflow: {'non_existent_col'}", result.error)

        # Should throw error for select column not existing
        set_string(self.importcols_pval, '')
        set_string(self.colnames_pval, 'non_existent_col')
        result = JoinURL.render(self.wfm, self.table)
        self.assertEqual("Key columns not in target workflow: {'non_existent_col'}", result.error)

    def test_type_num_cast(self):
        # Joining on column that is both int and float, module should convert to float
        version = self.wfm.store_fetched_table(self.ext_workflow_with_types)
        self.wfm.set_fetched_data_version(version)
        set_string(self.url_pval, self.valid_workflow_URL)
        set_string(self.colnames_pval, 'key')

        set_integer(self.type_pval, _join_type_map.index("inner"))
        result = JoinURL.render(self.wfm, self.table_with_types)
        assert_frame_equal(self.ref_left_join_with_types, result.dataframe)

    def test_type_mismatch(self):
        # Joining on column with different dtypes should fail
        set_string(self.url_pval, self.valid_workflow_URL)
        set_string(self.colnames_pval, 'key')

        set_integer(self.type_pval, _join_type_map.index("inner"))
        result = JoinURL.render(self.wfm, self.table_with_types)
        self.assertEqual(("Types do not match for key column 'key' (number and text). " \
                        'Please use a type conversion module to make these column types consistent.'), result.error)
