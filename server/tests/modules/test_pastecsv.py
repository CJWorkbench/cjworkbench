from server.tests.utils import *
from server.execute import execute_nocache
import pandas as pd
import io

# ---- PasteCSV ----

class PasteCSVTests(LoggedInTestCase):
    def setUp(self):
        super(PasteCSVTests, self).setUp()  # log in

        self.wf_module = load_and_add_module('pastecsv')  # creates workflow too
        self.csv_pval = get_param_by_id_name('csv')

        self.count_csv = 'Month,Amount\nJan,10\nFeb,5\nMar,10\n'
        self.count_tsv = 'Month\tAmount\nJan\t10\nFeb\t5\nMar\t10\n'

        self.table = pd.read_csv(io.StringIO(self.count_csv))  # should be same as TSV-derived table

    def test_empty(self):
        set_string(self.csv_pval, '')
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(pd.DataFrame()))  # No input, no output

    def test_csv(self):
        set_string(self.csv_pval, self.count_csv)
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))

    def test_tsv(self):
        set_string(self.csv_pval, self.count_tsv)
        out = execute_nocache(self.wf_module)
        self.assertTrue(out.equals(self.table))
