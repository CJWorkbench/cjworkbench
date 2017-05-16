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
        self.query_pval.string = 'Feb'
        self.query_pval.save()
        self.colnames_pval.string = 'Month'
        self.colnames_pval.save()

        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '  Month  Amount\n1   Feb      20')

        # Case sensitive - should return nothing because no match
        self.query_pval.string = 'feb'
        self.query_pval.save()
        self.case_pval.boolean = True
        self.case_pval.save()

        out = execute_wfmodule(self.wf_module)
        self.assertTrue(out.empty)

        # Regex
        self.query_pval.string = 'Jan|Feb'
        self.query_pval.save()
        self.regex_pval.boolean = True
        self.regex_pval.save()

        out = execute_wfmodule(self.wf_module)
        self.assertEqual(str(out), '  Month  Amount\n0   Jan      10\n1   Feb      20')


