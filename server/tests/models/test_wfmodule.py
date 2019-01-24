import io
import pandas as pd
from server.models import ModuleVersion, Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase, mock_csv_table


mock_csv_text2 = """Month,Amount,Name
Jan,10,Alicia Aliciason
Feb,666,Fred Frederson
"""
mock_csv_table2 = pd.read_csv(io.StringIO(mock_csv_text2))


# Set up a simple pipeline on test data
class WfModuleTests(DbTestCase):
    def test_retrieve_table_error_missing_version(self):
        '''
        If user selects a version and then the version disappers, no version is
        selected; return `None`.

        Returning `None` is kinda arbitrary. Another option is to return the
        latest version; but then, what if the caller also looks at
        wf_module.stored_data_version? The two values would be inconsistent.
        '''
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = pd.DataFrame({'A': [1]})
        table2 = pd.DataFrame({'B': [2]})
        stored_object1 = wf_module.store_fetched_table(table1)
        wf_module.store_fetched_table(table2)
        wf_module.stored_data_version = stored_object1
        wf_module.save()
        wf_module.stored_objects.get(stored_at=stored_object1).delete()
        wf_module.refresh_from_db()
        self.assertIsNone(wf_module.retrieve_fetched_table())

    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = wf_module.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save and recover data
        firstver = wf_module.store_fetched_table(table1)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(wf_module.stored_data_version, firstver) # should not switch versions by itself
        self.assertIsNone(wf_module.retrieve_fetched_table()) # no stored version, no table
        wf_module.stored_data_version = firstver
        wf_module.save()
        tableout1 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # create another version
        secondver = wf_module.store_fetched_table(table2)
        self.assertNotEqual(wf_module.stored_data_version, secondver) # should not switch versions by itself
        self.assertNotEqual(firstver, secondver)
        wf_module.stored_data_version = secondver
        wf_module.save()
        tableout2 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

        # change the version back
        wf_module.stored_data_version = firstver
        wf_module.save()
        tableout1 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout1.equals(table1))

        # list versions
        verlist = wf_module.list_fetched_data_versions()
        correct_verlist = [secondver, firstver] # sorted by creation date, latest first
        self.assertListEqual([ver[0] for ver in verlist], correct_verlist)

    def test_wf_module_store_table_if_different(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        table1 = mock_csv_table
        table2 = mock_csv_table2

        # nothing ever stored
        nothing = wf_module.retrieve_fetched_table()
        self.assertIsNone(nothing)

        # save a table
        ver1 = wf_module.store_fetched_table(table1)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(wf_module.stored_data_version, ver1) # should not switch versions by itself
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 1)

        # try saving it again, should be NOP
        verdup = wf_module.store_fetched_table_if_different(table1)
        self.assertIsNone(verdup)
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 1)

        # save something different now, should create new version
        ver2 = wf_module.store_fetched_table_if_different(table2)
        wf_module.save()
        wf_module.refresh_from_db()
        self.assertNotEqual(ver2, ver1)
        self.assertNotEqual(wf_module.stored_data_version, ver2) # should not switch versions by itself
        self.assertEqual(len(wf_module.list_fetched_data_versions()), 2)
        wf_module.stored_data_version = ver2
        wf_module.save()
        tableout2 = wf_module.retrieve_fetched_table()
        self.assertTrue(tableout2.equals(table2))

    def test_wf_module_duplicate(self):
        workflow = Workflow.create_and_init()
        wfm1 = workflow.tabs.first().wf_modules.create(order=0)

        # store data to test that it is duplicated
        s1 = wfm1.store_fetched_table(mock_csv_table)
        s2 = wfm1.store_fetched_table(mock_csv_table2)
        wfm1.secrets = {'do not copy': {'name': 'evil', 'secret': 'evil'}}
        wfm1.stored_data_version = s2
        wfm1.save()
        self.assertEqual(len(wfm1.list_fetched_data_versions()), 2)

        # duplicate into another workflow, as we would do when duplicating a workflow
        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wfm1d = wfm1.duplicate(tab2)
        wfm1d.refresh_from_db()  # test what we actually have in the db

        self.assertEqual(wfm1d.workflow, workflow2)
        self.assertEqual(wfm1d.module_version, wfm1.module_version)
        self.assertEqual(wfm1d.order, wfm1.order)
        self.assertEqual(wfm1d.notes, wfm1.notes)
        self.assertEqual(wfm1d.last_update_check, wfm1.last_update_check)
        self.assertEqual(wfm1d.is_collapsed, wfm1.is_collapsed)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        self.assertEqual(wfm1d.params, wfm1.params)
        self.assertEqual(wfm1d.secrets, {})

        # Stored data should contain a clone of content only, not complete version history
        self.assertIsNotNone(wfm1d.stored_data_version)
        self.assertEqual(wfm1d.stored_data_version, wfm1.stored_data_version)
        self.assertTrue(wfm1d.retrieve_fetched_table().equals(wfm1.retrieve_fetched_table()))
        self.assertEqual(len(wfm1d.list_fetched_data_versions()), 1)

    def test_wf_module_duplicate_disable_auto_update(self):
        """
        Duplicates should be lightweight by default: no auto-updating.
        """
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(order=0, auto_update_data=True,
                                          update_interval=600)

        workflow2 = Workflow.create_and_init()
        InitWorkflowCommand.create(workflow2)
        tab2 = workflow2.tabs.create(position=0)
        wf_module2 = wf_module.duplicate(tab2)

        self.assertEqual(wf_module2.auto_update_data, False)
        self.assertEqual(wf_module2.update_interval, 600)

    def test_wf_module_duplicate_clear_secrets(self):
        """
        Duplicates get new owners, so they should not copy secrets.
        """
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            secrets={'auth': {'name': 'x', 'secret': 'y'}}
        )

        workflow2 = Workflow.create_and_init()
        tab2 = workflow2.tabs.first()
        wf_module2 = wf_module.duplicate(tab2)

        self.assertEqual(wf_module2.secrets, {})

    def test_module_version_lookup(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'floob',
            'name': 'Floob',
            'category': 'Clean',
            'parameters': []
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='floob'
        )
        self.assertEqual(wf_module.module_version, module_version)
        # white-box testing: test that we work even from cache
        self.assertEqual(wf_module.module_version, module_version)

    def test_module_version_missing(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='floob'
        )
        self.assertIsNone(wf_module.module_version)
