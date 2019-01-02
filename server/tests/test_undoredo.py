import asyncio
from concurrent.futures import ThreadPoolExecutor
import django.db
from unittest.mock import patch
from server.models import Delta, ModuleVersion, Workflow
from server.models.commands import AddModuleCommand, ChangeParametersCommand, \
        ChangeWorkflowTitleCommand, ChangeWfModuleNotesCommand
from server.tests.utils import DbTestCase
from server.versions import WorkflowUndo, WorkflowRedo


async def async_noop(*args, **kwargs):
    pass


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class UndoRedoTests(DbTestCase):
    def setUp(self):
        super().setUp()

        # We'll execute with a 1-worker thread pool. That's because Django
        # database methods will spin up new connections and never close them.
        # (@database_sync_to_async -- which execute uses --only closes _old_
        # connections, not valid ones.)
        #
        # This hack is just for unit tests: we need to close all connections
        # before the test ends, so we can delete the entire database when tests
        # finish. We'll schedule the "close-connection" operation on the same
        # thread as @database_sync_to_async's blocking code ran on. That way,
        # it'll close the connection @database_sync_to_async was using.
        self._old_loop = asyncio.get_event_loop()
        self.loop = asyncio.new_event_loop()
        self.loop.set_default_executor(ThreadPoolExecutor(1))
        asyncio.set_event_loop(self.loop)

    # Be careful, in these tests, not to run database queries in async blocks.
    def tearDown(self):
        def close_thread_connection():
            # Close the connection that was created by @database_sync_to_async.
            # Assumes we're running in the same thread that ran the database
            # stuff.
            django.db.connections.close_all()

        self.loop.run_in_executor(None, close_thread_connection)

        asyncio.set_event_loop(self._old_loop)

        super().tearDown()

    def _run_async(self, task):
        return self.loop.run_until_complete(task)

    def assertWfModuleVersions(self, tab, expected_versions):
        result = list(
            tab.live_wf_modules.values_list('last_relevant_delta_id',
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
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'pastecsv',
            'name': 'pastecsv',
            'category': 'Cat',
            'parameters': [
                {'id_name': 'csv', 'type': 'string'},
            ]
        })

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()

        all_modules = tab.live_wf_modules  # beginning state: nothing

        v0 = workflow.last_delta_id

        # Test undoing nothing at all. Should NOP
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v0)
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(workflow.last_delta_id, v0)

        # Add a module
        cmd1 = self._run_async(AddModuleCommand.create(
            workflow=workflow,
            tab=tab,
            module_id_name='pastecsv',
            position=0,
            param_values={}
        ))
        v1 = cmd1.id
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertGreater(v1, v0)
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertWfModuleVersions(tab, [v1])

        # Undo, ensure we are back at start
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 0)
        self.assertEqual(workflow.last_delta_id, v0)
        self.assertWfModuleVersions(tab, [])

        # Redo, ensure we are back at v1
        self._run_async(WorkflowRedo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertWfModuleVersions(tab, [v1])

        # Change a parameter
        cmd2 = self._run_async(ChangeParametersCommand.create(
            workflow=workflow,
            wf_module=tab.live_wf_modules.first(),
            new_values={'csv': 'some value'}
        ))
        v2 = cmd2.id
        workflow.refresh_from_db()
        self.assertEqual(
            tab.live_wf_modules.first()
                .get_params().get_param_string('csv'),
            'some value'
        )
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertGreater(v2, v1)
        self.assertWfModuleVersions(tab, [v2])

        # Undo parameter change
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v1)
        self.assertEqual(
            tab.live_wf_modules.first()
                .get_params().get_param_string('csv'),
            ''
        )
        self.assertWfModuleVersions(tab, [v1])

        # Redo
        self._run_async(WorkflowRedo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertEqual(
            tab.live_wf_modules.first()
                .get_params().get_param_string('csv'),
            'some value'
        )
        self.assertWfModuleVersions(tab, [v2])

        # Redo again should do nothing
        self._run_async(WorkflowRedo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v2)
        self.assertEqual(
            tab.live_wf_modules.first()
                .get_params().get_param_string('csv'),
            'some value'
        )
        self.assertWfModuleVersions(tab, [v2])

        # Add one more command so the stack is 3 deep
        cmd3 = self._run_async(ChangeWorkflowTitleCommand.create(
            workflow=workflow,
            new_value='New Title'
        ))
        v3 = cmd3.id
        self.assertGreater(v3, v2)
        self.assertWfModuleVersions(tab, [v2])

        # Undo twice
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd2)
        self.assertWfModuleVersions(tab, [v2])
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd1)
        self.assertWfModuleVersions(tab, [v1])

        # Redo twice
        self._run_async(WorkflowRedo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd2)
        self.assertWfModuleVersions(tab, [v2])
        self._run_async(WorkflowRedo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd3)
        self.assertWfModuleVersions(tab, [v2])

        # Undo again to get to a place where we have two commands to redo
        self._run_async(WorkflowUndo(workflow))
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta, cmd1)

        # Now add a new command. It should remove cmd2, cmd3 from the redo
        # stack and delete them from the db
        wfm = all_modules.first()
        cmd4 = self._run_async(ChangeWfModuleNotesCommand.create(
            workflow=workflow,
            wf_module=wfm,
            new_value='Note of no note'
        ))
        v4 = cmd4.id
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v4)
        self.assertEqual(set(Delta.objects.values_list('id', flat=True)),
                         {v0, v1, v4})  # v2, v3 deleted

        # Undo back to start, then add a command, ensure it deletes dangling
        # commands (tests an edge case in Delta.save)
        self._run_async(WorkflowUndo(workflow))
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v1)
        cmd5 = self._run_async(ChangeWfModuleNotesCommand.create(
            workflow=workflow,
            wf_module=cmd1.wf_module,
            new_value='Note of some note'
        ))
        v5 = cmd5.id
        workflow.refresh_from_db()
        self.assertEqual(workflow.last_delta_id, v5)
        self.assertEqual(set(Delta.objects.values_list('id', flat=True)),
                         {v0, v1, v5})  # v1, v4 deleted
        self.assertWfModuleVersions(tab, [v1])
