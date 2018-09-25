from asgiref.sync import async_to_sync
from server.models import AddModuleCommand, ChangeParameterCommand, \
        ChangeWorkflowTitleCommand, ChangeWfModuleNotesCommand, Delta
from server.tests.utils import DbTestCase, load_module_version, \
        add_new_workflow, get_param_by_id_name
from server.versions import WorkflowUndo, WorkflowRedo


class UndoRedoTests(DbTestCase):
    def setUp(self):
        # Define two types of modules we are going to use
        self.csv = load_module_version('pastecsv')
        self.workflow = add_new_workflow('My Undoable Workflow')

    def assertWfModuleVersions(self, expected_versions):
        result = list(
            self.workflow.wf_modules.values_list('last_relevant_delta_id',
                                                 flat=True)
        )
        self.assertEqual(result, expected_versions)

    # Many things tested here:
    #  - Undo with 0,1,2 commands in stack
    #  - Redo with 0,1,2 commands to redo
    #  - Start with 3 commands in stack, then undo, undo, new command -> blow
    #    away commands 2,3
    # Command types used here are arbitrary, but different so that we test
    # polymorphism
    def test_undo_redo(self):
        all_modules = self.workflow.wf_modules  # beginning state: nothing
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta_id, None)

        v0 = self.workflow.revision()

        # Test undoing nothing at all. Should NOP
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.revision(), v0)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta_id, None)

        # Add a module
        cmd1 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.csv, 0)
        self.assertEqual(all_modules.count(), 1)
        self.assertNotEqual(self.workflow.last_delta_id, None)
        v1 = self.workflow.revision()
        self.assertGreater(v1, v0)
        self.assertWfModuleVersions([v1])

        # Undo, ensure we are back at start
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.revision(), v0)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(self.workflow.last_delta_id, None)
        self.assertWfModuleVersions([])

        # Redo, ensure we are back at v1
        async_to_sync(WorkflowRedo)(self.workflow)
        self.assertEqual(all_modules.count(), 1)
        self.assertNotEqual(self.workflow.last_delta_id, None)
        self.assertEqual(self.workflow.revision(), v1)
        self.assertWfModuleVersions([v1])

        # Change a parameter
        pval = get_param_by_id_name('csv')
        cmd2 = async_to_sync(ChangeParameterCommand.create)(pval, 'some value')
        self.assertEqual(pval.value, 'some value')
        self.workflow.refresh_from_db()
        v2 = self.workflow.revision()
        self.assertGreater(v2, v1)
        self.assertWfModuleVersions([v2])

        # Undo parameter change
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.revision(), v1)
        pval.refresh_from_db()
        self.assertEqual(pval.value, '')
        self.assertWfModuleVersions([v1])

        # Redo
        async_to_sync(WorkflowRedo)(self.workflow)
        self.assertEqual(self.workflow.revision(), v2)
        pval.refresh_from_db()
        self.assertEqual(pval.value, 'some value')
        self.assertWfModuleVersions([v2])

        # Redo again should do nothing
        async_to_sync(WorkflowRedo)(self.workflow)
        self.assertEqual(self.workflow.revision(), v2)
        self.assertEqual(pval.value, 'some value')
        self.assertWfModuleVersions([v2])

        # Add one more command so the stack is 3 deep
        cmd3 = async_to_sync(ChangeWorkflowTitleCommand.create)(self.workflow,
                                                                "New Title")
        # self.workflow.refresh_from_db()
        v3 = self.workflow.revision()
        self.assertGreater(v3, v2)
        self.assertWfModuleVersions([v2])

        # Undo twice
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd2)
        self.assertWfModuleVersions([v2])
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd1)
        self.assertWfModuleVersions([v1])

        # Redo twice
        async_to_sync(WorkflowRedo)(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd2)
        self.assertWfModuleVersions([v2])
        async_to_sync(WorkflowRedo)(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd3)
        self.assertWfModuleVersions([v2])

        # Undo again to get to a place where we have two commands to redo
        async_to_sync(WorkflowUndo)(self.workflow)
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertEqual(self.workflow.last_delta, cmd1)

        # Now add a new command. It should remove cmd2, cmd3 from the redo
        # stack and delete them from the db
        wfm = all_modules.first()
        cmd4 = async_to_sync(ChangeWfModuleNotesCommand.create)(
            wfm,
            "Note of no note"
        )
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd4)
        self.assertFalse(Delta.objects.filter(pk=cmd2.id).exists())
        self.assertFalse(Delta.objects.filter(pk=cmd3.id).exists())

        # Undo back to start, then add a command, ensure it deletes dangling
        # commands (tests an edge case in Delta.save)
        self.assertEqual(Delta.objects.count(), 2)
        async_to_sync(WorkflowUndo)(self.workflow)
        async_to_sync(WorkflowUndo)(self.workflow)
        self.assertIsNone(self.workflow.last_delta)
        cmd5 = async_to_sync(ChangeWfModuleNotesCommand.create)(
            wfm,
            "Note of some note"
        )
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd5)
        self.assertFalse(Delta.objects.filter(pk=cmd1.id).exists())
        self.assertFalse(Delta.objects.filter(pk=cmd4.id).exists())
        self.assertWfModuleVersions([v1])
