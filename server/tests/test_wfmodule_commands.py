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

        # undo
        cmd.backward()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(WfModule.objects.first(), existing_module)

        # nevermind, redo
        cmd.forward()
        self.assertEqual(all_modules.count(), 0)


class ChangeDataVersionCommandTests(TestCase):
    def setUp(self):
        self.workflow = create_testdata_workflow()
        self.wfm = WfModule.objects.first()

    # Change version, then undo/redo
    def test_change_data_version(self):
        # Create two data versions, use the second
        firstver = self.wfm.store_data('text1')
        secondver = self.wfm.store_data('text2')
        self.wfm.set_stored_data_version(secondver)

        start_rev = self.workflow.revision()

        # Change back to first version
        cmd = ChangeDataVersionCommand.create(self.wfm, firstver)
        self.assertEqual(self.wfm.get_stored_data_version(), firstver)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), start_rev)

        # undo
        cmd.backward()
        self.assertEqual(self.wfm.get_stored_data_version(), secondver)

        # redo
        cmd.forward()
        self.assertEqual(self.wfm.get_stored_data_version(), firstver)


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
