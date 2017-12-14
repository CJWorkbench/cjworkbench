from server.models import AddModuleCommand,DeleteModuleCommand,ChangeDataVersionCommand
from server.models import ChangeWfModuleNotesCommand,ChangeWfModuleUpdateSettingsCommand
from django.test import TestCase
from server.tests.utils import *
from django.utils import timezone


class AddDeleteModuleCommandTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.module_version = ModuleVersion.objects.first()   # defined by create_testdata_workflow

    # Add another module, then undo, redo
    def test_add_module(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        start_rev = self.workflow.revision()

        # Add a module, insert before the existing one, check to make sure it went there and old one is after
        cmd = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=0)
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), start_rev)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo! undo! ahhhhh everything is on fire! undo!
        cmd.backward()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(WfModule.objects.first(), existing_module)

        # wait no, we wanted that module
        cmd.forward()
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling WfModule too
        cmd.backward()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(WfModule.objects.first(), existing_module)
        cmd.delete()
        self.assertFalse(WfModule.objects.filter(pk=added_module.id).exists()) # should be gone


    # Try inserting at various positions to make sure the renumbering works right
    # Then undo multiple times
    def test_add_many_modules(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()
        self.assertEqual(existing_module.order, 0)

        # Insert at beginning
        cmd1 = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=0)
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.wf_module.order, 0)
        self.assertNotEqual(cmd1.wf_module, existing_module)

        # Insert at end
        cmd2 = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=2)
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.wf_module.order, 2)

        # Insert in between two modules
        cmd3 = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=2)
        self.assertEqual(all_modules.count(), 4)
        self.assertEqual(cmd3.wf_module.order, 2)

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
        cmd3.backward()
        cmd2.backward()
        cmd1.backward()
        self.assertEqual(all_modules.count(), 1)


    # Delete module, then undo, redo
    def test_delete_module(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        start_rev = self.workflow.revision()

        # Delete it. Yeah, you better run.
        cmd = DeleteModuleCommand.create(existing_module)
        self.assertEqual(all_modules.count(), 0)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), start_rev)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo
        cmd.backward()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(WfModule.objects.first(), existing_module)

        # nevermind, redo
        cmd.forward()
        self.assertEqual(all_modules.count(), 0)

        # Deleting the appplied command should delete dangling WfModule too
        cmd.delete()
        self.assertFalse(WfModule.objects.filter(pk=existing_module.id).exists())  # should be gone

    # We had a bug where add then delete caused an error when deleting workflow,
    # since both commands tried to delete the WfModule
    def test_add_delete(self):
        cmda = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=0)
        cmdd = DeleteModuleCommand.create(cmda.wf_module)
        self.workflow.delete()


class ChangeDataVersionCommandTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm = WfModule.objects.first()

    # Change version, then undo/redo
    def test_change_data_version(self):
        # Create two data versions, use the second
        firstver = self.wfm.store_fetched_table(mock_csv_table)
        secondver = self.wfm.store_fetched_table(mock_csv_table2)
        self.wfm.set_fetched_data_version(secondver)

        start_rev = self.workflow.revision()

        # Change back to first version
        cmd = ChangeDataVersionCommand.create(self.wfm, firstver)
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), start_rev)

        # undo
        cmd.backward()
        self.assertEqual(self.wfm.get_fetched_data_version(), secondver)

        # redo
        cmd.forward()
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)


class ChangeWfModuleNotesCommandTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm = WfModule.objects.first()

    # Change notes, then undo/redo
    def test_change_notes(self):
        firstNote = 'text1'
        secondNote = 'text2'
        self.wfm.notes = firstNote

        # do
        cmd = ChangeWfModuleNotesCommand.create(self.wfm, secondNote)
        self.assertEqual(self.wfm.notes, secondNote)

        # undo
        cmd.backward()
        self.assertEqual(self.wfm.notes, firstNote)

        # redo
        cmd.forward()
        self.assertEqual(self.wfm.notes, secondNote)


class ChangeWfModuleUpdateSettingsCommandTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm = WfModule.objects.first()

    # Change notes, then undo/redo
    def test_change_update_settings(self):

        self.wfm.auto_update_data = False
        self.wfm.next_update = None
        self.wfm.update_interval = 100

        # do
        mydate = timezone.now()
        cmd = ChangeWfModuleUpdateSettingsCommand.create(self.wfm, True, mydate, 1000)
        self.assertTrue(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, mydate)
        self.assertEqual(self.wfm.update_interval, 1000)

        # undo
        cmd.backward()
        self.assertFalse(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, None)
        self.assertEqual(self.wfm.update_interval, 100)

        # redo
        cmd.forward()
        self.assertTrue(self.wfm.auto_update_data)
        self.assertEqual(self.wfm.next_update, mydate)
        self.assertEqual(self.wfm.update_interval, 1000)
