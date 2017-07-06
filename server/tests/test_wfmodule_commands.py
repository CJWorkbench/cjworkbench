from server.models import AddModuleCommand,DeleteModuleCommand
from django.test import TestCase
from server.tests.utils import *

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

        start_rev = self.workflow.revision

        # Add a module, insert before the existing one, check to make sure it went there and old one is after
        cmd = AddModuleCommand.create(self.workflow, module_version=self.module_version, insert_before=0)
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision, start_rev)

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

        start_rev = self.workflow.revision

        # Delete it. Yeah, you better run.
        cmd = DeleteModuleCommand.create(existing_module)
        self.assertEqual(all_modules.count(), 0)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision, start_rev)

        # undo
        cmd.backward()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(WfModule.objects.first(), existing_module)

        # nevermind, redo
        cmd.forward()
        self.assertEqual(all_modules.count(), 0)
