import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from unittest.mock import Mock, patch
import django.db
import pandas as pd
from server.tests.utils import DbTestCase
from server.execute import execute_workflow, UnneededExecution
from server.models import LoadedModule, Workflow
from server.models.commands import InitWorkflowCommand
from server.modules.types import ProcessResult


logger = logging.getLogger(__name__)


fake_future = asyncio.Future()
fake_future.set_result(None)


async def fake_send(*args, **kwargs):
    pass


def cached_render_result_revision_list(workflow):
    return list(workflow.wf_modules.values_list(
        'cached_render_result_delta_id',
        flat=True
    ))


class ExecuteTests(DbTestCase):
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

    def _execute(self, workflow):
        with self.assertLogs():  # hide all logs
            logger.info('message so assertLogs() passes when no log messages')

            self.loop.run_until_complete(execute_workflow(workflow))

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_new_revision(self, fake_load_module):
        workflow = Workflow.objects.create()
        delta1 = InitWorkflowCommand.create(workflow)
        wf_module = workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta1.id
        )

        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module.cache_render_result(delta1.id, result1)
        wf_module.save()

        result2 = ProcessResult(pd.DataFrame({'B': [2]}))
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module.last_relevant_delta_id = delta2.id
        wf_module.save(update_fields=['last_relevant_delta_id'])

        fake_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_module
        fake_module.render.return_value = result2

        self._execute(workflow)

        wf_module.refresh_from_db()
        self.assertEqual(
            wf_module.get_cached_render_result(only_fresh=True).result,
            result2
        )

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_execute_race_delete_workflow(self, fake_load_module):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        wf_module2 = workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )

        def load_module_and_delete(module_version):
            workflow.delete()
            fake_module = Mock(LoadedModule)
            result = ProcessResult(pd.DataFrame({'A': [1]}))
            fake_module.render.return_value = result
            return fake_module
        fake_load_module.side_effect = load_module_and_delete

        with self.assertRaises(UnneededExecution):
            self._execute(workflow)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async')
    def test_execute_mark_unreachable(self, send_delta_async,
                                      fake_load_module):
        send_delta_async.return_value = fake_future

        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        wf_module2 = workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )
        wf_module3 = workflow.wf_modules.create(
            order=2,
            last_relevant_delta_id=delta.id
        )

        fake_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_module
        fake_module.render.return_value = ProcessResult(error='foo')

        self._execute(workflow)

        wf_module1.refresh_from_db()
        self.assertEqual(wf_module1.get_cached_render_result().status, 'error')
        self.assertEqual(wf_module1.get_cached_render_result().result,
                         ProcessResult(error='foo'))

        wf_module2.refresh_from_db()
        self.assertEqual(wf_module2.get_cached_render_result().status,
                         'unreachable')
        self.assertEqual(wf_module2.get_cached_render_result().result,
                         ProcessResult())

        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.get_cached_render_result().status,
                         'unreachable')
        self.assertEqual(wf_module3.get_cached_render_result().result,
                         ProcessResult())

        send_delta_async.assert_called_with(workflow.id, {
            'updateWfModules': {
                str(wf_module3.id): {
                    'output_status': 'unreachable',
                    'quick_fixes': [],
                    'output_error': '',
                    'output_columns': [],
                    'output_n_rows': 0,
                    'last_relevant_delta_id': delta.id,
                    'cached_render_result_delta_id': delta.id,
                }
            }
        })

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_cache_hit(self, fake_module):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module1.cache_render_result(delta.id, result1)
        wf_module1.save()
        wf_module2 = workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )
        result2 = ProcessResult(pd.DataFrame({'B': [2]}))
        wf_module2.cache_render_result(delta.id, result2)
        wf_module2.save()

        fake_module.assert_not_called()

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_resume_without_rerunning_unneeded_renders(self, fake_load_module):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        wf_module1 = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id
        )
        result1 = ProcessResult(pd.DataFrame({'A': [1]}))
        wf_module1.cache_render_result(delta.id, result1)
        wf_module1.save()
        wf_module2 = workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=delta.id
        )

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [2]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        wf_module2.refresh_from_db()
        actual = wf_module2.get_cached_render_result().result
        self.assertEqual(actual, result2)
        fake_loaded_module.render.assert_called_once()  # only with module2

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    @patch('server.notifications.email_output_delta')
    def test_email_delta(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        delta1 = InitWorkflowCommand.create(workflow)
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta2.id
        )
        wf_module.cache_render_result(
            delta1.id,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )
        wf_module.notifications = True
        wf_module.save()

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [2]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        email.assert_called()

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    @patch('server.notifications.email_output_delta')
    def test_email_no_delta_when_not_changed(self, email, fake_load_module):
        workflow = Workflow.objects.create()
        delta1 = InitWorkflowCommand.create(workflow)
        delta2 = InitWorkflowCommand.create(workflow)
        wf_module = workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta2.id
        )
        wf_module.cache_render_result(
            delta1.id,
            ProcessResult(pd.DataFrame({'A': [1]}))
        )
        wf_module.notifications = True
        wf_module.save()

        fake_loaded_module = Mock(LoadedModule)
        fake_load_module.return_value = fake_loaded_module
        result2 = ProcessResult(pd.DataFrame({'A': [1]}))
        fake_loaded_module.render.return_value = result2

        self._execute(workflow)

        email.assert_not_called()
