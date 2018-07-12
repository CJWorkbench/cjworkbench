import pandas
from server.tests.utils import create_testdata_workflow, load_and_add_module, get_param_by_id_name, LoggedInTestCase
from server.modules.pythoncode import PythonCode


class PythonCodeTest(LoggedInTestCase):
    def setUp(self):
        super(PythonCodeTest, self).setUp()  # log in
        workflow = create_testdata_workflow()
        self.wf_module = load_and_add_module('pythoncode', workflow=workflow)
        self.code_pval = get_param_by_id_name('code')

    def _run_code(self, code):
        self.code_pval.value = code
        self.code_pval.save()

        return PythonCode.render(self.wf_module, pandas.DataFrame())

    def test_render(self):
        out = self._run_code("""
def process(table):
    columns = ['A','B', 'C']
    data = np.array([np.arange(5)]*3).T
    return pd.DataFrame(columns=columns, data=data)
        """)

        self.assertEqual(str(out), "   A  B  C\n0  0  0  0\n1  1  1  1\n2  2  2  2\n3  3  3  3\n4  4  4  4")

    def test_builtins(self):
        # Use `list`, `str` and `int` to test they exist and work as intended
        out = self._run_code("""
def process(table):
    return pd.DataFrame({'data': list([str('foo'), int('3')])})
        """)

        self.assertEqual(str(out), "  data\n0  foo\n1    3")

    def test_no_import(self):
        out = self._run_code("""
import typing

def process(table):
    return table
        """)

        self.assertEqual(out,
                         'Line 1: __import__ disabled in Python Code module')
