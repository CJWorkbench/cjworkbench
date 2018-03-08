from django.test import TestCase
from server.tests.utils import *
from server.execute import execute_nocache

# ---- Python Code  ----

class PythonCodeTest(LoggedInTestCase):
    def setUp(self):
        super(PythonCodeTest, self).setUp()  # log in
        workflow = create_testdata_workflow()
        self.wf_module = load_and_add_module('pythoncode', workflow=workflow)
        self.code_pval = get_param_by_id_name('code')

    def test_render(self):
        # Replace the output with our own data

        code = "columns = ['A','B', 'C']\ndata = np.array([np.arange(5)]*3).T\nreturn pd.DataFrame(columns=columns, data=data)";
        self.code_pval.value = code
        self.code_pval.save()

        out = execute_nocache(self.wf_module)
        self.assertEqual(str(out), "   A  B  C\n0  0  0  0\n1  1  1  1\n2  2  2  2\n3  3  3  3\n4  4  4  4")

