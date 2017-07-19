from server.models import AddModuleCommand,ChangeParameterCommand
from django.test import TestCase
from server.tests.utils import *
from server.versions import *

class UndoRedoTests(TestCase):
    def setUp(self):
        # Define two types of modules we are going to use
        self.csv = load_module_version('pastecsv')
        self.workflow = add_new_workflow('My Undoable Workflow')

    # Add a module, then change parameter value, then undo & redo
    # Start from scratch to test edge cases of empty command chain
    # We use two different types of commands here to ensure that polymorphism is working right
    def test_undo_redo(self):
        # beginning state: nothing
        all_modules = WfModule.objects.filter(workflow=self.workflow) # filter so we pick up only "attached" modules
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        start_rev = self.workflow.revision()

        # Test undoing nothing at all. Should NOP
        WorkflowUndo(self.workflow)
        #self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.revision(), start_rev)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        # Add a module
        AddModuleCommand.create(self.workflow, self.csv, 0)
        #self.workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertNotEqual(self.workflow.last_delta, None)
        rev1 = self.workflow.revision()
        self.assertGreater(rev1, start_rev)

        # Undo, ensure we are back at start
        WorkflowUndo(self.workflow)
        #self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.revision(), start_rev)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        # Redo, ensure we are back at rev1
        WorkflowRedo(self.workflow)
        #self.workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertNotEqual(self.workflow.last_delta, None)
        self.assertEqual(self.workflow.revision(), rev1)

        # Change a parameter
        pval = get_param_by_id_name('csv')
        cmd = ChangeParameterCommand.create(pval, 'some value')
        self.assertEqual(pval.string, 'some value')
        self.workflow.refresh_from_db()
        rev2 = self.workflow.revision()
        self.assertGreater(rev2, rev1)

        # Undo parameter change
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.revision(), rev1)
        pval.refresh_from_db()
        self.assertEqual(pval.string, '')

        # Redo
        WorkflowRedo(self.workflow)
        self.assertEqual(self.workflow.revision(), rev2)
        pval.refresh_from_db()
        self.assertEqual(pval.string, 'some value')

        # Redo again should do nothing
        WorkflowRedo(self.workflow)
        self.assertEqual(self.workflow.revision(), rev2)
        self.assertEqual(pval.string, 'some value')

