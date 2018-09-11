import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
from server.modules.concaturl import ConcatURL
from server.modules.types import ProcessResult
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        mock_csv_path, add_new_workflow, set_string, set_checkbox, \
        set_integer, get_param_by_id_name
from server.modules.concaturl import _type_map, _source_column_name

class ConcatURLTests(LoggedInTestCase):
    def setUp(self):
        super(ConcatURLTests, self).setUp()  # log in
        self.wfm = load_and_add_module('concaturl')
        self.url_pval = get_param_by_id_name('url')
        self.source_columns_pval = get_param_by_id_name('source_columns')
        self.type_pval = get_param_by_id_name('type')
        self.csv_table = pd.read_csv(mock_csv_path)

        self.valid_workflow_URL = 'https://app.workbenchdata.com/workflows/2/'

        self.table = pd.DataFrame([['a', 'b'], ['a', 'c']], columns=['col1', 'key'])
        self.ext_workflow = pd.DataFrame([['b', 'c'], ['d', 'a']], columns=['key', 'col2'])

        self.ref_source_only_concat = pd.DataFrame([['a', 'b'], ['a', 'c'], [np.NaN, 'b'], [np.NaN, 'd']],
                                             columns=['col1', 'key'])

        self.ref_inner_concat = pd.DataFrame(['b', 'c', 'b', 'd'], columns=['key'])

        self.ref_outer_concat = pd.DataFrame([['a', np.NaN, 'b'], ['a', np.NaN, 'c'],
                                              [np.NaN, 'c', 'b'], [np.NaN, 'a', 'd']],
                                             columns=['col1', 'col2', 'key'])

    def test_first_applied(self):
        # no upload state
        version = self.wfm.store_fetched_table(None)
        self.wfm.set_fetched_data_version(version)
        result = ConcatURL.render(self.wfm, None)
        self.assertEqual(result, ProcessResult())

        # Upload state but empty datagrid
        version = self.wfm.store_fetched_table(self.table)
        self.wfm.set_fetched_data_version(version)
        result = ConcatURL.render(self.wfm, None)
        self.assertEqual(result, ProcessResult())

    def test_invalid_url(self):
        version = self.wfm.store_fetched_table(self.csv_table)
        self.wfm.set_fetched_data_version(version)

        set_string(self.url_pval, 'not a url')

        result = ConcatURL.render(self.wfm, self.table)
        self.assertTrue('URL' in result.error)

        # Working, non-workflow URL should fail
        set_string(self.url_pval, 'www.google.com')

        result = ConcatURL.render(self.wfm, self.table)
        self.assertTrue('URL' in result.error)

    def test_concat(self):
        version = self.wfm.store_fetched_table(self.ext_workflow)
        self.wfm.set_fetched_data_version(version)
        set_string(self.url_pval, self.valid_workflow_URL)
        set_checkbox(self.source_columns_pval, False)

        set_integer(self.type_pval, _type_map.index("only include this workflow's columns"))
        result = ConcatURL.render(self.wfm, self.table)
        # Sanitize dataframe to clean index created by pandas concat()
        result.sanitize_in_place()
        assert_frame_equal(self.ref_source_only_concat, result.dataframe)

        set_integer(self.type_pval, _type_map.index("only include matching columns"))
        result = ConcatURL.render(self.wfm, self.table)
        # Sanitize dataframe to clean index created by pandas concat()
        result.sanitize_in_place()
        assert_frame_equal(self.ref_inner_concat, result.dataframe)

        set_integer(self.type_pval, _type_map.index("include columns from both workflows"))
        result = ConcatURL.render(self.wfm, self.table)
        # Sanitize dataframe to clean index created by pandas concat()
        result.sanitize_in_place()
        assert_frame_equal(self.ref_outer_concat, result.dataframe)

    def test_concat_with_source(self):
        version = self.wfm.store_fetched_table(self.ext_workflow)
        self.wfm.set_fetched_data_version(version)
        set_string(self.url_pval, self.valid_workflow_URL)
        set_checkbox(self.source_columns_pval, True)

        set_integer(self.type_pval, _type_map.index("include columns from both workflows"))
        result = ConcatURL.render(self.wfm, self.table)
        # Sanitize dataframe to clean index created by pandas concat()
        result.sanitize_in_place()

        ref = self.ref_outer_concat.copy()
        ref.insert(0, _source_column_name, ['Current', 'Current', '2', '2'])

        assert_frame_equal(ref, result.dataframe)
