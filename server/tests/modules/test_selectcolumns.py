import io
import pandas
from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name, mock_csv_text
from server.execute import execute_wfmodule
from server.models.WfModule import WfModule
from server.modules.types import ProcessResult

mock_csv_table = pandas.read_csv(io.StringIO(mock_csv_text))


class SelectColumnsTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()  # log in
        workflow = create_testdata_workflow()
        self.wf_module = load_and_add_module('selectcolumns',
                                             workflow=workflow)
        self.cols_pval = get_param_by_id_name('colnames')

    def test_render_single_column(self):
        self.cols_pval.value = 'Month'
        self.cols_pval.save()
        result = execute_wfmodule(self.wf_module)
        expected = ProcessResult(mock_csv_table[['Month']])
        self.assertEqual(result, expected)

    def test_render_strip_whitespace(self):
        self.cols_pval.value = 'Month '
        self.cols_pval.save()
        result = execute_wfmodule(self.wf_module)
        expected = ProcessResult(mock_csv_table[['Month']])
        self.assertEqual(result, expected)

    def test_render_maintain_input_column_order(self):
        self.cols_pval.value = 'Amount,Month'
        self.cols_pval.save()
        result = execute_wfmodule(self.wf_module)
        expected = ProcessResult(mock_csv_table[['Month', 'Amount']])
        self.assertEqual(result, expected)

    def test_render_ignore_invalid_column_name(self):
        self.cols_pval.value = 'Amountxxx,Month'
        self.cols_pval.save()
        result = execute_wfmodule(self.wf_module)
        expected = ProcessResult(mock_csv_table[['Month']])
        self.assertEqual(result, expected)
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.status, WfModule.READY)
