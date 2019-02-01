import asyncio
from contextlib import contextmanager
from unittest.mock import patch
import msgpack
from server.models import Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase
from server.worker import execute
from server.worker.render import handle_render, render_or_reschedule
from server.worker.pg_locker import WorkflowAlreadyLocked


future_none = asyncio.Future()
future_none.set_result(None)


class Rescheduler:
    def __init__(self):
        self.calls = []

    async def reschedule(self, *args):
        self.calls.append(args)


class SuccessfulRenderLocker:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    @classmethod
    def render_lock(cls, workflow_id):
        return cls(workflow_id)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FailedRenderLocker:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id

    @classmethod
    def render_lock(cls, workflow_id):
        return cls(workflow_id)

    async def __aenter__(self):
        raise WorkflowAlreadyLocked

    async def __aexit__(self, exc_type, exc, tb):
        pass


class RenderTest(DbTestCase):
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
                await handle_render(None, None, FakeRender())
                self.assertEqual(cm.output, [
                    ('INFO:server.worker.render:Ignoring invalid render '
                     'request. Expected {workflow_id:int, delta_id:int}; got '
                     "{'workflow_id': 123}"),
                ])

        self.run_with_async_db(inner())

    @patch('server.worker.execute.execute_workflow')
    def test_render_or_reschedule_render(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        with self.assertLogs():
            self.run_with_async_db(render_or_reschedule(
                SuccessfulRenderLocker,
                rescheduler.reschedule,
                workflow.id,
                delta.id
            ))

        execute.assert_called_with(workflow)
        self.assertEqual(rescheduler.calls, [])

    @patch('server.worker.execute.execute_workflow')
    def test_render_or_reschedule_reschedule(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await render_or_reschedule(FailedRenderLocker,
                                           rescheduler.reschedule,
                                           workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    (f'INFO:server.worker.render:Workflow {workflow.id} is '
                     'being rendered elsewhere; rescheduling'),
                ])

        self.run_with_async_db(inner())

        execute.assert_not_called()
        self.assertEqual(rescheduler.calls, [(workflow.id, delta.id)])

    def test_render_or_reschedule_wrong_delta_id(self):
        rescheduler = Rescheduler()
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await render_or_reschedule(SuccessfulRenderLocker,
                                           rescheduler.reschedule,
                                           workflow.id, delta.id - 1)
                self.assertEqual(cm.output, [
                    (f'INFO:server.worker.render:Ignoring stale render request'
                     f' {delta.id - 1} for Workflow {workflow.id}'),
                ])

        self.run_with_async_db(inner())

    def test_render_or_reschedule_workflow_not_found(self):
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await render_or_reschedule(SuccessfulRenderLocker,
                                           rescheduler.reschedule, 12345, 1)
                self.assertEqual(cm.output, [
                    ('INFO:server.worker.render:Skipping render of deleted '
                     'Workflow 12345'),
                ])

        self.run_with_async_db(inner())

    @patch('server.worker.execute.execute_workflow')
    def test_render_or_reschedule_aborted(self, mock_execute):
        mock_execute.side_effect = execute.UnneededExecution
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await render_or_reschedule(SuccessfulRenderLocker,
                                           rescheduler.reschedule,
                                           workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    ('INFO:server.worker.render:UnneededExecution in '
                     f'execute_workflow({workflow.id})')
                ])

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        # Don't reschedule: it is _unneeded_ execution.
        self.assertEqual(rescheduler.calls, [])
