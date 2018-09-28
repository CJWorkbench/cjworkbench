from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.utils import timezone
from server.models import AddModuleCommand, DeleteModuleCommand, \
        ChangeDataVersionCommand, ChangeWfModuleNotesCommand, \
        ChangeWfModuleUpdateSettingsCommand, ModuleVersion, WfModule
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        mock_csv_table, mock_csv_table2


async def async_noop(*args, **kwargs):
    pass


class CommandTestCase(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = create_testdata_workflow()

    def assertWfModuleVersions(self, expected_versions):
        result = list(
            self.workflow.wf_modules.values_list('last_relevant_delta_id',
                                                 flat=True)
        )
        self.assertEqual(result, expected_versions)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class AddDeleteModuleCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        # defined by create_testdata_workflow
        self.module_version = ModuleVersion.objects.first()

    # Add another module, then undo, redo
    def test_add_module(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # Add a module, insert before the existing one, check to make sure it
        # went there and old one is after
        cmd = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                     self.module_version, 0,
                                                     {'csv': 'A,B\n1,2'}
        )
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        # Test that supplied param is written
        self.assertEqual(
            len(added_module.parameter_vals.filter(value='A,B\n1,2')),
            1
        )
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo! undo! ahhhhh everything is on fire! undo!
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)

        # wait no, we wanted that module
        async_to_sync(cmd.forward)()
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling
        # WfModule too
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)
        cmd.delete()
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=added_module.id)  # should be gone

    # Try inserting at various positions to make sure the renumbering works
    # right Then undo multiple times
    def test_add_many_modules(self):
        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # beginning state: one WfModule
        all_modules = self.workflow.wf_modules
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()
        self.assertEqual(existing_module.order, 0)
        self.assertWfModuleVersions([v1])

        # Insert at beginning
        cmd1 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      0, {})
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.wf_module.order, 0)
        self.assertNotEqual(cmd1.wf_module, existing_module)
        v2 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2])

        # Insert at end
        cmd2 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      2, {})
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.wf_module.order, 2)
        v3 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2, v3])

        # Insert in between two modules
        cmd3 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      2, {})
        self.assertEqual(all_modules.count(), 4)
        self.assertEqual(cmd3.wf_module.order, 2)
        v4 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2, v4, v4])

        # Check the delta chain, should be 1 <-> 2 <-> 3
        self.workflow.refresh_from_db()
        cmd1.refresh_from_db()
        cmd2.refresh_from_db()
        cmd3.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd3)
        self.assertIsNone(cmd3.next_delta)
        self.assertEqual(cmd3.prev_delta, cmd2)
        self.assertEqual(cmd2.next_delta, cmd3)
        self.assertEqual(cmd2.prev_delta, cmd1)
        self.assertEqual(cmd1.next_delta, cmd2)
        self.assertIsNone(cmd1.prev_delta)

        # We should be able to go all the way back
        async_to_sync(cmd3.backward)()
        self.assertWfModuleVersions([v2, v2, v3])
        async_to_sync(cmd2.backward)()
        self.assertWfModuleVersions([v2, v2])
        async_to_sync(cmd1.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(all_modules.count(), 1)

    # Delete module, then undo, redo
    def test_delete_module(self):
        # beginning state: one WfModule
        all_modules = self.workflow.wf_modules
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()
        self.assertWfModuleVersions([v1])

        # Delete it. Yeah, you better run.
        cmd = async_to_sync(DeleteModuleCommand.create)(existing_module)
        self.assertEqual(all_modules.count(), 0)
        self.assertWfModuleVersions([])

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        v2 = self.workflow.revision()
        self.assertGreater(v2, v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertWfModuleVersions([v1])
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)

        # nevermind, redo
        async_to_sync(cmd.forward)()
        self.assertEqual(all_modules.count(), 0)

        # Deleting the appplied command should delete dangling WfModule too
        cmd.delete()
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=existing_module.id)  # should be gone

    # ensure that deleting the selected module sets the selected module to
    # null, and is undoable
    def test_delete_selected(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.selected_wf_module = 0
        self.workflow.save()

        cmd = async_to_sync(DeleteModuleCommand.create)(existing_module)

        self.workflow.refresh_from_db()
        self.assertIsNone(self.workflow.selected_wf_module)

        async_to_sync(cmd.backward)()
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.selected_wf_module, 0)

    # ensure that adding a module, selecting it, then undo add, prevents
    # dangling selected_wf_module (basically the AddModule equivalent of
    # test_delete_selected)
    def test_add_undo_selected(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)

        cmd = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                     self.module_version,
                                                     1, {})

        self.workflow.selected_wf_module = cmd.wf_module.order
        self.workflow.save()

        async_to_sync(cmd.backward)()

        self.workflow.refresh_from_db()
        self.assertIsNone(self.workflow.selected_wf_module)

    # We had a bug where add then delete caused an error when deleting
    # workflow, since both commands tried to delete the WfModule
    def test_add_delete(self):
        cmda = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      0, {})
        async_to_sync(DeleteModuleCommand.create)(cmda.wf_module)
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeDataVersionCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.wfm = WfModule.objects.first()

    # Change version, then undo/redo
    def test_change_data_version(self):
        # Create two data versions, use the second
        firstver = self.wfm.store_fetched_table(mock_csv_table)
        secondver = self.wfm.store_fetched_table(mock_csv_table2)

        self.wfm.set_fetched_data_version(secondver)

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # Change back to first version
        cmd = async_to_sync(ChangeDataVersionCommand.create)(self.wfm,
                                                             firstver)
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)

        self.workflow.refresh_from_db()
        v2 = self.workflow.revision()
        # workflow revision should have been incremented
        self.assertGreater(v2, v1)
        self.assertWfModuleVersions([v2])

        # undo
        async_to_sync(cmd.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(self.wfm.get_fetched_data_version(), secondver)

        # redo
        async_to_sync(cmd.forward)()
        self.assertWfModuleVersions([v2])
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleNotesCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.wfm = WfModule.objects.first()

    # Change notes, then undo/redo
    def test_change_notes(self):
        firstNote = 'text1'
        secondNote = 'text2'
        self.wfm.notes = firstNote

        # do
        cmd = async_to_sync(ChangeWfModuleNotesCommand.create)(self.wfm,
                                                               secondNote)
        self.assertEqual(self.wfm.notes, secondNote)

        # undo
        async_to_sync(cmd.backward)()
        self.assertEqual(self.wfm.notes, firstNote)

        # redo
        async_to_sync(cmd.forward)()
        self.assertEqual(self.wfm.notes, secondNote)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleUpdateSettingsCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.wfm = WfModule.objects.first()

    # Change notes, then undo/redo
    def test_change_update_settings(self):
        self.wfm.auto_update_data = False
        self.wfm.next_update = None
        self.wfm.update_interval = 100

        # do
        mydate = timezone.now()
        cmd = async_to_sync(ChangeWfModuleUpdateSettingsCommand.create)(
            self.wfm,
            True,
            mydate,
            1000
        )
        self.assertTrue(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, mydate)
        self.assertEqual(self.wfm.update_interval, 1000)

        # undo
        async_to_sync(cmd.backward)()
        self.assertFalse(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, None)
        self.assertEqual(self.wfm.update_interval, 100)

        # redo
        async_to_sync(cmd.forward)()
        self.assertTrue(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, mydate)
        self.assertEqual(self.wfm.update_interval, 1000)
