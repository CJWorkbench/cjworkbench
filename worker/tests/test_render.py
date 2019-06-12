import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock, patch
import msgpack
from server.models import Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import DbTestCase
from worker import execute
from worker.render import handle_render, render_workflow_and_maybe_requeue
from worker.pg_render_locker import WorkflowAlreadyLocked


future_none = asyncio.Future()
future_none.set_result(None)


class _RenderLock:
    def __init__(self):
        self.stalled = False

    async def stall_others(self):
        self.stalled = True


class SuccessfulRenderLocker:
    @asynccontextmanager
    async def render_lock(self, workflow_id):
        lock = _RenderLock()
        try:
            yield lock
        finally:
            assert lock.stalled


class FailedRenderLocker:
    @asynccontextmanager
    async def render_lock(self, workflow_id):
        raise WorkflowAlreadyLocked
        yield  # otherwise, Python 3.7, it isn't an asynccontextmanager.


async def async_noop(*args, **kwargs):
    pass


class RenderTest(DbTestCase):
    def test_handle_render_invalid_message(self):
        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await handle_render({'workflow_id': 123}, None, None)
                self.assertEqual(cm.output, [
                    ('INFO:worker.render:Ignoring invalid render '
                     'request. Expected {workflow_id:int, delta_id:int}; got '
                     "{'workflow_id': 123}"),
                ])

        self.run_with_async_db(inner())

    @patch('worker.execute.execute_workflow')
    def test_render_happy_path(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        ack = Mock(name='ack', side_effect=async_noop)
        requeue = Mock(name='requeue', side_effect=async_noop)

        with self.assertLogs():
            self.run_with_async_db(render_workflow_and_maybe_requeue(
                SuccessfulRenderLocker(),
                workflow.id,
                delta.id,
                ack,
                requeue,
            ))

        execute.assert_called_with(workflow, delta.id)
        ack.assert_called()
        requeue.assert_not_called()

    @patch('worker.execute.execute_workflow')
    def test_render_other_worker_rendering_so_skip(self, execute):
        execute.side_effect = async_noop
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        ack = Mock(name='ack', side_effect=async_noop)
        requeue = Mock(name='requeue', side_effect=async_noop)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_workflow_and_maybe_requeue(
                    FailedRenderLocker(),
                    workflow.id,
                    delta.id,
                    ack,
                    requeue,
                )
                self.assertEqual(cm.output, [
                    (f'INFO:worker.render:Workflow {workflow.id} is '
                     'being rendered elsewhere; ignoring'),
                ])

        self.run_with_async_db(inner())

        execute.assert_not_called()
        ack.assert_called()
        requeue.assert_not_called()

    @patch('worker.execute.execute_workflow')
    def test_render_unknown_error_so_crash(self, execute):
        # Test what happens when our `worker.execute` module is buggy and
        # raises something it shouldn't raise.
        execute.side_effect = FileNotFoundError
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        ack = Mock(name='ack', side_effect=async_noop)
        requeue = Mock(name='requeue', side_effect=async_noop)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(),
                    workflow.id,
                    delta.id,
                    ack,
                    requeue,
                )
                self.assertRegex(
                    cm.output[0],
                    '^ERROR:worker.render:Error during render of workflow \d+'
                )

        self.run_with_async_db(inner())
        ack.assert_called()
        requeue.assert_not_called()

    def test_render_workflow_not_found_skip(self):
        ack = Mock(name='ack', return_value=future_none)
        requeue = Mock(name='requeue', return_value=future_none)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(),
                    12345,
                    1,
                    ack,
                    requeue,
                )
                self.assertEqual(cm.output, [
                    ('INFO:worker.render:Skipping render of deleted '
                     'Workflow 12345'),
                ])

        self.run_with_async_db(inner())
        requeue.assert_not_called()
        ack.assert_called()

    @patch('worker.execute.execute_workflow')
    def test_render_unneeded_execution_so_requeue(self, mock_execute):
        mock_execute.side_effect = execute.UnneededExecution
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        ack = Mock(name='ack', side_effect=async_noop)
        requeue = Mock(name='requeue', side_effect=async_noop)

        async def inner():
            with self.assertLogs('worker', level='INFO') as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(),
                    workflow.id,
                    delta.id,
                    ack,
                    requeue,
                )
                self.assertEqual(cm.output, [
                    (f'INFO:worker.render:UnneededExecution in '
                     f'execute_workflow({workflow.id}, {delta.id})')
                ])

        self.run_with_async_db(inner())
        ack.assert_called()
        requeue.assert_called_with(workflow.id, delta.id)
