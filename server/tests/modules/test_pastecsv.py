import io
import pandas as pd
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        get_param_by_id_name, set_string
from server.execute import execute_wfmodule
from server.modules.types import ProcessResult

count_csv = 'Month,Amount\nJan,10\nFeb,5\nMar,10\n'
count_tsv = 'Month\tAmount\nJan\t10\nFeb\t5\nMar\t10\n'
reference_table = pd.read_csv(io.StringIO(count_csv))  # same table as TSV


class PasteCSVTests(LoggedInTestCase):
    def setUp(self):
        super(PasteCSVTests, self).setUp()  # log in

        self.wf_module = load_and_add_module('pastecsv')  # creates workflow
        self.csv_pval = get_param_by_id_name('csv')

    def test_empty(self):
        set_string(self.csv_pval, '')
        result = execute_wfmodule(self.wf_module)
        self.assertEqual(result, ProcessResult(pd.DataFrame()))

    def test_csv(self):
        set_string(self.csv_pval, count_csv)
        result = execute_wfmodule(self.wf_module)
        self.assertEqual(result, ProcessResult(reference_table))

    def test_tsv(self):
        set_string(self.csv_pval, count_tsv)
        result = execute_wfmodule(self.wf_module)
        self.assertEqual(result, ProcessResult(reference_table))
