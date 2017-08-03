from server.models import AddModuleCommand,ChangeParameterCommand, ChangeWorkflowTitleCommand, ChangeWfModuleNotesCommand
from django.test import TestCase
from server.tests.utils import *
from server.versions import *

class UndoRedoTests(TestCase):
    def setUp(self):
        # Define two types of modules we are going to use
        self.csv = load_module_version('pastecsv')
        self.workflow = add_new_workflow('My Undoable Workflow')

    # Many things tested here:
    #  - Undo with 0,1,2 commands in stack
    #  - Redo with 0,1,2 commands to redo
    #  - Start with 3 commands in stack, then undo, undo, new command -> blow away commands 2,3
    # Command types used here are arbitrary, but different so that we test polymorphism
    def test_undo_redo(self):
        # beginning state: nothing
        all_modules = WfModule.objects.filter(workflow=self.workflow) # filter so we pick up only "attached" modules
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        start_rev = self.workflow.revision()

        # Test undoing nothing at all. Should NOP
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.revision(), start_rev)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        # Add a module
        cmd1 = AddModuleCommand.create(self.workflow, self.csv, 0)
        self.assertEqual(all_modules.count(), 1)
        wfm = WfModule.objects.first()
        self.assertNotEqual(self.workflow.last_delta, None)
        rev1 = self.workflow.revision()
        self.assertGreater(rev1, start_rev)

        # Undo, ensure we are back at start
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.revision(), start_rev)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta, None)

        # Redo, ensure we are back at rev1
        WorkflowRedo(self.workflow)
        self.assertEqual(all_modules.count(), 1)
        self.assertNotEqual(self.workflow.last_delta, None)
        self.assertEqual(self.workflow.revision(), rev1)

        # Change a parameter
        pval = get_param_by_id_name('csv')
        cmd2 = ChangeParameterCommand.create(pval, 'some value')
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

        # Add one more command so the stack is 3 deep
        cmd3 = ChangeWorkflowTitleCommand.create(self.workflow, "Hot New Title")
        # self.workflow.refresh_from_db()
        rev3 = self.workflow.revision()
        self.assertGreater(rev3, rev2)

        # Undo twice
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd2)
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd1)

        # Redo twice
        WorkflowRedo(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd2)
        WorkflowRedo(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd3)

        # Undo again to get to a place where we have two commands to redo
        WorkflowUndo(self.workflow)
        WorkflowUndo(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd1)

        # Now add a new command. It should remove cmd2, cmd3 from the redo stack and delete them from the db
        cmd4 = ChangeWfModuleNotesCommand.create(wfm, "Note of no note")
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd4)
        #self.assertFalse(Delta.objects.filter(pk=cmd2.id).exists())
        #self.assertFalse(Delta.objects.filter(pk=cmd3.id).exists())

        # Undo back to start, then add a command, ensure it deletes dangling commands
        # (tests an edge case in Delta.save)
        # self.assertEqual(Delta.objects.count(), 2)
        WorkflowUndo(self.workflow)
        WorkflowUndo(self.workflow)
        self.assertIsNone(self.workflow.last_delta)
        cmd5 = ChangeWfModuleNotesCommand.create(wfm, "Note of some note")
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd5)
        #self.assertFalse(Delta.objects.filter(pk=cmd1.id).exists())
#self.assertFalse(Delta.objects.filter(pk=cmd4.id).exists())

