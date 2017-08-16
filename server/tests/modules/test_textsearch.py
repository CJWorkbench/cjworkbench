from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_wfmodule

# ---- TextSearch ----

class TextSearchTest(LoggedInTestCase):
    def setUp(self):
        super(TextSearchTest, self).setUp()  # log in
        workflow = create_testdata_workflow()
        module_def = load_module_def('textsearch')
        self.wf_module = load_and_add_module(workflow, module_def)
        self.query_pval = get_param_by_id_name('query')
        self.colnames_pval = get_param_by_id_name('colnames')
        self.case_pval = get_param_by_id_name('casesensitive')
        self.regex_pval = get_param_by_id_name('regex')

    def test_render(self):
        # No columns specified, no output
        out = execute_wfmodule(self.wf_module)
        self.assertTrue(out.empty)

        # Basic search
        self.query_pval.set_value('Feb')
        self.colnames_pval.set_value('Month')

        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '  Month  Amount\n1   Feb      20')

        # Case sensitive - should return nothing because no match
        self.query_pval.set_value('feb')
        self.case_pval.set_value(True)

        out = execute_wfmodule(self.wf_module)
        self.assertTrue(out.empty)

        # Regex
        self.query_pval.set_value('Jan|Feb')
        self.regex_pval.set_value(True)

        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '  Month  Amount\n0   Jan      10\n1   Feb      20')


