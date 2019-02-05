import asyncio
from contextlib import contextmanager
from unittest.mock import Mock, patch
import msgpack
from server.models import Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase
from worker import execute
from worker.render import handle_render, render_or_requeue, DupRenderWait
from worker.pg_locker import WorkflowAlreadyLocked


future_none = asyncio.Future()
future_none.set_result(None)


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
        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await handle_render(None, {'workflow_id': 123}, None)
                self.assertEqual(cm.output, [
                    ('INFO:worker.render:Ignoring invalid render '
                     'request. Expected {workflow_id:int, delta_id:int}; got '
                     "{'workflow_id': 123}"),
                ])

        self.run_with_async_db(inner())

    @patch('worker.execute.execute_workflow')
    def test_render_or_requeue_render(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        requeue = Mock(name='requeue', return_value=future_none)

        with self.assertLogs():
            self.run_with_async_db(render_or_requeue(
                SuccessfulRenderLocker,
                requeue,
                workflow.id,
                delta.id
            ))

        execute.assert_called_with(workflow)
        requeue.assert_not_called()

    @patch('worker.execute.execute_workflow')
    def test_render_or_requeue_requeue(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        requeue = Mock(name='requeue', return_value=future_none)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_or_requeue(FailedRenderLocker, requeue,
                                        workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    (f'INFO:worker.render:Workflow {workflow.id} is '
                     'being rendered elsewhere; rescheduling'),
                ])

        self.run_with_async_db(inner())

        execute.assert_not_called()
        requeue.assert_called_with(DupRenderWait)

    def test_render_or_requeue_wrong_delta_id(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        requeue = Mock(name='requeue', return_value=future_none)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_or_requeue(SuccessfulRenderLocker, requeue,
                                        workflow.id, delta.id - 1)
                self.assertEqual(cm.output, [
                    (f'INFO:worker.render:Ignoring stale render request'
                     f' {delta.id - 1} for Workflow {workflow.id}'),
                ])

        self.run_with_async_db(inner())

    def test_render_or_requeue_workflow_not_found(self):
        requeue = Mock(name='requeue', return_value=future_none)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_or_requeue(SuccessfulRenderLocker, requeue,
                                        12345, 1)
                self.assertEqual(cm.output, [
                    ('INFO:worker.render:Skipping render of deleted '
                     'Workflow 12345'),
                ])

        self.run_with_async_db(inner())

    @patch('worker.execute.execute_workflow')
    def test_render_or_requeue_aborted(self, mock_execute):
        mock_execute.side_effect = execute.UnneededExecution
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        requeue = Mock(name='requeue', return_value=future_none)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_or_requeue(SuccessfulRenderLocker,
                                        requeue, workflow.id, delta.id)
                self.assertEqual(cm.output, [
                    ('INFO:worker.render:UnneededExecution in '
                     f'execute_workflow({workflow.id})')
                ])

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        # Don't requeue: it is _unneeded_ execution.
        requeue.assert_not_called()
