import io
from django.core.exceptions import ValidationError
import pandas as pd
from server.models import ParameterSpec, WfModule, ParameterVal, Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        add_new_module_version, add_new_parameter_spec, add_new_wf_module, \
        mock_csv_table, mock_csv_table2, add_new_workflow

# Set up a simple pipeline on test data
# Our WfModule unit tests derive from this, below, and WfModule view tests also use this
class WfModuleTestsBase(DbTestCase):
    def createTestWorkflow(self):
        # Create a standard test workflow, but it has only one module so add two more to test render pipeline
        # Throw a missing value in there to test handling of NA values
        test_csv = 'Class,M,F\n' \
                   'math,10,12\n' \
                   'english,,7\n' \
                   'history,11,13\n' \
                   'economics,20,20'

        self.test_table = pd.read_csv(io.StringIO(test_csv), header=0, skipinitialspace=True)

        self.workflow1 = create_testdata_workflow(csv_text=test_csv)
        self.pspec11 = ParameterSpec.objects.get(id_name='csv')

        self.module2_version = add_new_module_version('Module 2', dispatch='NOP')
        self.pspec21 = add_new_parameter_spec(self.module2_version, ParameterSpec.STRING, def_value='foo')
        self.pspec22 = add_new_parameter_spec(self.module2_version, ParameterSpec.FLOAT, def_value=3.14)
        self.pspec23 = add_new_parameter_spec(self.module2_version, ParameterSpec.INTEGER, def_value=42)
        self.pspec24 = add_new_parameter_spec(self.module2_version, ParameterSpec.CHECKBOX, def_value=True)
        self.pspec25 = ParameterSpec.objects.create(module_version=self.module2_version,
                                                    type=ParameterSpec.MENU,
                                                    def_items='Apple|Banana|Kittens',
                                                    def_value='1')

        self.module3_version = add_new_module_version('Module 3', dispatch='double_M_col')
        self.pspec31 = add_new_parameter_spec(self.module3_version, ParameterSpec.BUTTON)

        self.wfmodule1 = WfModule.objects.get(order=0)
        self.wfmodule2 = add_new_wf_module(self.workflow1, self.module2_version, 1)
        self.wfmodule3 = add_new_wf_module(self.workflow1, self.module3_version, 2)


class WfModuleTests(WfModuleTestsBase):
    # check that creating a wf_module correctly sets up new ParameterVals w/ defaults from ParameterSpec
    def test_default_parameters(self):
        self.createTestWorkflow()

        pval = ParameterVal.objects.get(parameter_spec=self.pspec21, wf_module=self.wfmodule2)
        self.assertEqual(pval.get_value(), 'foo')

        pval = ParameterVal.objects.get(parameter_spec=self.pspec22, wf_module=self.wfmodule2)
        self.assertEqual(pval.get_value(), 3.14)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec23, wf_module=self.wfmodule2)
        self.assertEqual(pval.get_value(), 42)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec24, wf_module=self.wfmodule2)
        self.assertEqual(pval.get_value(), True)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec25, wf_module=self.wfmodule2)
        self.assertEqual(pval.selected_menu_item_string(), 'Banana')

        # button has no value, so just checking existence here
        pval = ParameterVal.objects.get(parameter_spec=self.pspec31, wf_module=self.wfmodule3)
        self.assertEqual(pval.visible, True)

    def test_retrieve_table_error_missing_version(self):
        '''
        If user selects a version and then the version disappers, no version is
        selected; return `None`.

        Returning `None` is kinda arbitrary. Another option is to return the
        latest version; but then, what if the caller also looks at
        wf_module.stored_data_version? The two values would be inconsistent.
        '''
        self.createTestWorkflow()
        table1 = pd.DataFrame({'A': [1]})
        table2 = pd.DataFrame({'B': [2]})
        stored_object1 = self.wfmodule1.store_fetched_table(table1)
        self.wfmodule1.store_fetched_table(table2)
        self.wfmodule1.stored_data_version = stored_object1
        self.wfmodule1.save()
        self.wfmodule1.stored_objects.get(stored_at=stored_object1).delete()
        self.wfmodule1.refresh_from_db()
        self.assertIsNone(self.wfmodule1.retrieve_fetched_table())

    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        self.createTestWorkflow()
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = self.wfmodule1.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save and recover data
        firstver = self.wfmodule1.store_fetched_table(table1)
        self.wfmodule1.save()
        self.wfmodule1.refresh_from_db()
        self.assertNotEqual(self.wfmodule1.stored_data_version, firstver) # should not switch versions by itself
        self.assertIsNone(self.wfmodule1.retrieve_fetched_table()) # no stored version, no table
        self.wfmodule1.stored_data_version = firstver
        self.wfmodule1.save()
        tableout1 = self.wfmodule1.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # create another version
        secondver = self.wfmodule1.store_fetched_table(table2)
        self.assertNotEqual(self.wfmodule1.stored_data_version, secondver) # should not switch versions by itself
        self.assertNotEqual(firstver, secondver)
        self.wfmodule1.stored_data_version = secondver
        self.wfmodule1.save()
        tableout2 = self.wfmodule1.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

        # change the version back
        self.wfmodule1.stored_data_version = firstver
        self.wfmodule1.save()
        tableout1 = self.wfmodule1.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # list versions
        verlist = self.wfmodule1.list_fetched_data_versions()
        correct_verlist = [secondver, firstver] # sorted by creation date, latest first
        self.assertListEqual([ver[0] for ver in verlist], correct_verlist)

        # but like, none of this should have created versions on any other wfmodule
        self.assertEqual(self.wfmodule2.list_fetched_data_versions(), [])

    def test_wf_module_store_table_if_different(self):
        self.createTestWorkflow()
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = self.wfmodule1.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save a table
        ver1 = self.wfmodule1.store_fetched_table(table1)
        self.wfmodule1.save()
        self.wfmodule1.refresh_from_db()
        self.assertNotEqual(self.wfmodule1.stored_data_version, ver1) # should not switch versions by itself
        self.assertEqual(len(self.wfmodule1.list_fetched_data_versions()), 1)

        # try saving it again, should be NOP
        verdup = self.wfmodule1.store_fetched_table_if_different(table1)
        self.assertIsNone(verdup)
        self.assertEqual(len(self.wfmodule1.list_fetched_data_versions()), 1)

        # save something different now, should create new version
        ver2 = self.wfmodule1.store_fetched_table_if_different(table2)
        self.wfmodule1.save()
        self.wfmodule1.refresh_from_db()
        self.assertNotEqual(ver2, ver1)
        self.assertNotEqual(self.wfmodule1.stored_data_version, ver2) # should not switch versions by itself
        self.assertEqual(len(self.wfmodule1.list_fetched_data_versions()), 2)
        self.wfmodule1.stored_data_version = ver2
        self.wfmodule1.save()
        tableout2 = self.wfmodule1.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

    def test_wf_module_duplicate(self):
        self.createTestWorkflow()
        wfm1 = self.wfmodule1

        # store data to test that it is duplicated
        s1 = wfm1.store_fetched_table(mock_csv_table)
        s2 = wfm1.store_fetched_table(mock_csv_table2)
        wfm1.stored_data_version = s2
        wfm1.save()
        self.assertEqual(len(wfm1.list_fetched_data_versions()), 2)

        # duplicate into another workflow, as we would do when duplicating a workflow
        workflow2 = add_new_workflow("Test Workflow 2")
        InitWorkflowCommand.create(workflow2)
        wfm1d = wfm1.duplicate(workflow2)
        wfm1d.refresh_from_db() # test what we actually have in the db

        self.assertEqual(wfm1d.workflow, workflow2)
        self.assertEqual(wfm1d.module_version, wfm1.module_version)
        self.assertEqual(wfm1d.order, wfm1.order)
        self.assertEqual(wfm1d.notes, wfm1.notes)
        self.assertEqual(wfm1d.last_update_check, wfm1.last_update_check)
        self.assertEqual(wfm1d.is_collapsed, wfm1.is_collapsed)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)

        # parameters should be duplicated
        self.assertEqual(ParameterVal.objects.filter(wf_module=wfm1d).count(), ParameterVal.objects.filter(wf_module=wfm1).count())

        # Stored data should contain a clone of content only, not complete version history
        self.assertIsNotNone(wfm1d.stored_data_version)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        self.assertTrue(wfm1d.retrieve_fetched_table().equals(wfm1.retrieve_fetched_table()))
        self.assertEqual(len(wfm1d.list_fetched_data_versions()), 1)

    def test_wf_module_duplicate_disable_auto_update(self):
        """
        Duplicates should be lightweight by default: no auto-updating.
        """
        workflow = Workflow.objects.create()
        InitWorkflowCommand.create(workflow)
        wf_module = workflow.wf_modules.create(order=0, auto_update_data=True,
                                               update_interval=600)

        workflow2 = Workflow.objects.create()
        InitWorkflowCommand.create(workflow2)
        wf_module2 = wf_module.duplicate(workflow2)

        self.assertEqual(wf_module2.auto_update_data, False)
        self.assertEqual(wf_module2.update_interval, 600)
