import asyncio
from contextlib import contextmanager
import logging
from unittest.mock import Mock, patch
from asgiref.sync import async_to_sync
from dateutil import parser
import msgpack
import pandas as pd
from server import execute, worker
from server.models import LoadedModule, Workflow
from server.models.commands import InitWorkflowCommand
from server.modules.types import ProcessResult
from server.tests.utils import DbTestCase, load_module_version


future_none = asyncio.Future()
future_none.set_result(None)


class SuccessfulRenderLock:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FailedRenderLock:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    async def __aenter__(self):
        raise worker.WorkflowAlreadyLocked

    async def __aexit__(self, exc_type, exc, tb):
        pass


class Rescheduler:
    def __init__(self):
        self.calls = []

    async def reschedule(self, *args):
        self.calls.append(args)


class WorkerTest(DbTestCase):
    def test_handle_render_invalid_message(self):
        class FakeRender:
            @contextmanager
            def process(self):
                yield

            @property
            def body(self):
                return msgpack.packb({'workflow_id': 123})

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.handle_render(None, None, FakeRender())
                self.assertEqual(cm.output, [
                    ('INFO:server.worker:Ignoring invalid render request. '
                     'Expected {workflow_id:int, delta_id:int}; got '
                     "{'workflow_id': 123}"),
                ])

        async_to_sync(inner)()

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_render(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs():
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id, delta.id)

        async_to_sync(inner)()

        execute.assert_called_with(workflow)
        self.assertEqual(rescheduler.calls, [])

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_reschedule(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(FailedRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    (f'INFO:server.worker:Workflow {workflow.id} is being '
                     'rendered elsewhere; rescheduling'),
                ])

        async_to_sync(inner)()

        execute.assert_not_called()
        self.assertEqual(rescheduler.calls, [(workflow.id, delta.id)])

    def test_render_or_reschedule_wrong_delta_id(self):
        rescheduler = Rescheduler()
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id, delta.id - 1)
                self.assertEqual(cm.output, [
                    (f'INFO:server.worker:Ignoring stale render request '
                     f'{delta.id - 1} for Workflow {workflow.id}'),
                ])

        async_to_sync(inner)()

    def test_render_or_reschedule_workflow_not_found(self):
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  12345, 1)
                self.assertEqual(cm.output, [
                    ('INFO:server.worker:Skipping render of deleted '
                     'Workflow 12345'),
                ])

        async_to_sync(inner)()

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_aborted(self, mock_execute):
        mock_execute.side_effect = execute.UnneededExecution
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    ('INFO:server.worker:UnneededExecution in '
                     f'execute_workflow({workflow.id})')
                ])

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        # Don't reschedule: it is _unneeded_ execution.
        self.assertEqual(rescheduler.calls, [])


# Test the scan loop that updates all auto-updating modules
class UpdatesTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.loadurl = load_module_version('loadurl')
        self.wfm1 = self.workflow.wf_modules.create(
            module_version=self.loadurl,
            order=0
        )

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    @patch('server.versions.save_result_if_changed')
    def test_fetch_wf_module(self, save_result, load_module):
        result = ProcessResult(pd.DataFrame({'A': [1]}), error='hi')

        async def fake_fetch(*args, **kwargs):
            return result

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        now = parser.parse('Aug 28 1999 2:24:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:34PM UTC')

        with self.assertLogs(worker.__name__, logging.DEBUG):
            async_to_sync(worker.fetch_wf_module)(self.wfm1, now)

        save_result.assert_called_with(self.wfm1, result)

        self.wfm1.refresh_from_db()
        self.assertEqual(self.wfm1.last_update_check, now)
        self.assertEqual(self.wfm1.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_fetch_wf_module_skip_missed_update(self, load_module):
        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        load_module.side_effect = Exception('caught')  # least-code test case

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(worker.__name__):
            async_to_sync(worker.fetch_wf_module)(self.wfm1, now)

        self.wfm1.refresh_from_db()
        self.assertEqual(self.wfm1.next_update, due_for_update)

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync')
    def test_crashing_module(self, load_module):
        async def fake_fetch(*args, **kwargs):
            raise ValueError('boo')

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.fetch.side_effect = fake_fetch

        self.wfm1.next_update = parser.parse('Aug 28 1999 2:24PM UTC')
        self.wfm1.update_interval = 600
        self.wfm1.save()

        now = parser.parse('Aug 28 1999 2:34:02PM UTC')
        due_for_update = parser.parse('Aug 28 1999 2:44PM UTC')

        with self.assertLogs(worker.__name__, level='ERROR') as cm:
            # We should log the actual error
            async_to_sync(worker.fetch_wf_module)(self.wfm1, now)
            self.assertEqual(cm.records[0].exc_info[0], ValueError)

        self.wfm1.refresh_from_db()
        # [adamhooper, 2018-10-26] while fiddling with tests, I changed the
        # behavior to record the update check even when module fetch fails.
        # Previously, an exception would prevent updating last_update_check,
        # and I think that must be wrong.
        self.assertEqual(self.wfm1.last_update_check, now)
        self.assertEqual(self.wfm1.next_update, due_for_update)
