from server.tests.utils import LoggedInTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.models.StoredObject import StoredObject
from server.models.Commands import ChangeParameterCommand
from server.execute import execute_wfmodule
from server.modules.types import ProcessResult
import pandas as pd
import io
import mock


class ExecuteTests(LoggedInTestCase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(ExecuteTests, self).setUp()  # log in

        test_csv = 'Class,M,F\n' \
                   'math,10,12\n' \
                   'english,,7\n' \
                   'history,11,13\n' \
                   'economics,20,20'
        self.test_table = pd.read_csv(io.StringIO(test_csv))
        self.test_table_M = pd.DataFrame(self.test_table['M'])  # need DataFrame ctor otherwise we get series not df
        self.test_table_MF = self.test_table[['M', 'F']]

        # workflow pastes a CSV in then picks columns (by default all columns as cols_pval is empty)
        self.workflow = create_testdata_workflow(test_csv)
        self.wfm1 = self.workflow.wf_modules.first()
        self.wfm2 = load_and_add_module('selectcolumns', workflow=self.workflow)
        self.cols_pval = get_param_by_id_name('colnames')


    # seriously, don't crash on a new workflow (rev=0, no caches)
    def test_execute_first_revision(self):
        execute_wfmodule(self.wfm2)

    def test_execute(self):
        # create a rev that selects a column, so revision is not empty and workflow is not NOP
        ChangeParameterCommand.create(self.cols_pval, 'M')
        rev1 = str(self.workflow.revision())

        result = execute_wfmodule(self.wfm2)
        self.assertEqual(result, ProcessResult(self.test_table_M))

        # should have created two cached objects
        self.assertEqual(StoredObject.objects.count(), 2)
        so1 = StoredObject.objects.get(wf_module=self.wfm1)
        self.assertTrue(self.test_table.equals(so1.get_table()))
        self.assertEqual(so1.type, StoredObject.CACHED_TABLE)
        self.assertEqual(so1.metadata, rev1)

        so2 = StoredObject.objects.get(wf_module=self.wfm2)
        self.assertTrue(self.test_table_M.equals(so2.get_table()))
        self.assertEqual(so2.type, StoredObject.CACHED_TABLE)
        self.assertEqual(so2.metadata, rev1)

        # Change second module and render from there. Should bump revs.
        ChangeParameterCommand.create(self.cols_pval, 'M,F')
        self.workflow.refresh_from_db()
        rev2 = str(self.workflow.revision())
        self.assertNotEqual(rev1, rev2)

        result = execute_wfmodule(self.wfm2)
        self.assertEqual(result, ProcessResult(self.test_table_MF))

        self.assertEqual(StoredObject.objects.count(), 2)
        so1 = StoredObject.objects.get(wf_module=self.wfm1)
        self.assertTrue(self.test_table.equals(so1.get_table()))
        self.assertEqual(so1.metadata, rev2)

        so2 = StoredObject.objects.get(wf_module=self.wfm2)
        self.assertTrue(self.test_table_MF.equals(so2.get_table()))
        self.assertEqual(so2.metadata, rev2)

        # try rendering again with no revision changes, check that we hit the cache
        # that is, module_dispatch_render is never called
        with mock.patch('server.dispatch.module_dispatch_render') as mdr:
            result = execute_wfmodule(self.wfm2)
            self.assertEqual(result, ProcessResult(self.test_table_MF))
            self.assertFalse(mdr.called)


    # interesting case because duplicated workflow has no revisions/cached tables
    def test_duplicate_and_execute(self):
        workflow2 = self.workflow.duplicate(self.user)
        wfmd1, wfmd2 = list(workflow2.wf_modules.all())

        execute_wfmodule(wfmd2)

        self.assertEqual(StoredObject.objects.count(), 2)
        so1 = StoredObject.objects.get(wf_module=wfmd1)
        self.assertTrue(self.test_table.equals(so1.get_table()))

        so2 = StoredObject.objects.get(wf_module=wfmd2)
        self.assertTrue(self.test_table.equals(so2.get_table()))
