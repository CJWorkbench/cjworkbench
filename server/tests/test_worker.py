import asyncio
from unittest.mock import patch
from server import execute, worker
from server.models import Workflow
from server.tests.utils import DbTestCase


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
    def test_pg_locker(self):
        async def inner():
            async with worker.PgLocker() as locker1:
                async with worker.PgLocker() as locker2:
                    async with locker1.render_lock(1):
                        with self.assertRaises(worker.WorkflowAlreadyLocked):
                            async with locker2.render_lock(1):
                                pass

                    # do not raise WorkflowAlreadyLocked here
                    async with locker2.render_lock(1):
                        pass

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_render(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs():
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        execute.assert_called_with(workflow)
        self.assertEqual(rescheduler.calls, [])

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_reschedule(self, execute):
        execute.return_value = future_none
        workflow = Workflow.objects.create()
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(FailedRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id)
                self.assertEqual(cm.output, [
                    (f'INFO:server.worker:Workflow {workflow.id} is being '
                     'rendered elsewhere; rescheduling'),
                ])

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        execute.assert_not_called()
        self.assertEqual(rescheduler.calls, [(workflow.id,)])

    def test_render_or_reschedule_workflow_not_found(self):
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  12345)
                self.assertEqual(cm.output, [
                    'INFO:server.worker:Skipping render of deleted Workflow 12345',
                ])


        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

    @patch('server.execute.execute_workflow')
    def test_render_or_reschedule_aborted(self, mock_execute):
        mock_execute.side_effect = execute.UnneededExecution
        workflow = Workflow.objects.create()
        rescheduler = Rescheduler()

        async def inner():
            with self.assertLogs('server.worker', level='INFO') as cm:
                await worker.render_or_reschedule(SuccessfulRenderLock,
                                                  rescheduler.reschedule,
                                                  workflow.id)
                self.assertEqual(cm.output, [
                    ('INFO:server.worker:UnneededExecution in '
                     f'execute_workflow({workflow.id})')
                ])

        loop = asyncio.new_event_loop()
        loop.run_until_complete(inner())
        loop.close()

        # Don't reschedule: it is _unneeded_ execution.
        self.assertEqual(rescheduler.calls, [])
