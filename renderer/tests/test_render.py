from contextlib import asynccontextmanager
from unittest.mock import Mock, patch

from cjworkbench.pg_render_locker import WorkflowAlreadyLocked
from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase

from renderer import execute
from renderer.render import handle_render, render_workflow_and_maybe_requeue


async def async_noop(*args, **kwargs):
    pass


def async_err(err):
    async def inner(*args, **kwargs):
        raise err

    return inner


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


class RenderTest(DbTestCase):
    def test_handle_render_invalid_message(self):
        async def inner():
            with self.assertLogs("renderer", level="INFO") as cm:
                await handle_render({"workflow_id": 123}, None)
                self.assertEqual(
                    cm.output,
                    [
                        (
                            "INFO:renderer.render:Ignoring invalid render "
                            "request. Expected {workflow_id:int, delta_id:int}; got "
                            "{'workflow_id': 123}"
                        )
                    ],
                )

        self.run_with_async_db(inner())

    @patch.object(rabbitmq, "queue_render")
    @patch("renderer.execute.execute_workflow")
    def test_render_happy_path(self, execute, queue_render):
        execute.side_effect = async_noop
        workflow = Workflow.objects.create(last_delta_id=123)

        with self.assertLogs():
            self.run_with_async_db(
                render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(), workflow.id, 123
                )
            )

        execute.assert_called_with(workflow, 123)
        queue_render.assert_not_called()

    @patch("cjwstate.rabbitmq.queue_render")
    @patch("renderer.execute.execute_workflow")
    def test_render_other_renderer_rendering_so_skip(self, execute, queue_render):
        workflow = Workflow.objects.create(last_delta_id=123)

        async def inner():
            with self.assertLogs("renderer", level="INFO") as cm:
                await render_workflow_and_maybe_requeue(
                    FailedRenderLocker(), workflow.id, 123
                )
                self.assertEqual(
                    cm.output,
                    [
                        (
                            f"INFO:renderer.render:Workflow {workflow.id} is "
                            "being rendered elsewhere; ignoring"
                        )
                    ],
                )

        self.run_with_async_db(inner())

        execute.assert_not_called()
        queue_render.assert_not_called()

    @patch("cjwstate.rabbitmq.queue_render")
    @patch("renderer.execute.execute_workflow")
    def test_render_unknown_error_so_crash(self, execute, queue_render):
        # Test what happens when our `renderer.execute` module is buggy and
        # raises something it shouldn't raise.
        execute.side_effect = FileNotFoundError
        workflow = Workflow.objects.create(last_delta_id=123)

        async def inner():
            with self.assertLogs("renderer", level="INFO") as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(),
                    workflow.id,
                    123,
                )
                self.assertRegex(
                    cm.output[0],
                    r"^INFO:renderer.render:Start execute_workflow\(\d+, \d+\)",
                )
                self.assertRegex(
                    cm.output[1],
                    r"^INFO:renderer.render:End execute_workflow\(\d+, \d+\)",
                )
                self.assertRegex(
                    cm.output[2],
                    r"^ERROR:renderer.render:Error during render of workflow \d+\n",
                )
                self.assertEqual(len(cm.output), 3)

        self.run_with_async_db(inner())
        queue_render.assert_not_called()

    @patch("cjwstate.rabbitmq.queue_render")
    def test_render_workflow_not_found_skip(self, queue_render):
        async def inner():
            with self.assertLogs("renderer", level="INFO") as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(),
                    12345,
                    1,
                )
                self.assertEqual(
                    cm.output,
                    [
                        (
                            "INFO:renderer.render:Skipping render of deleted "
                            "Workflow 12345"
                        )
                    ],
                )

        self.run_with_async_db(inner())
        queue_render.assert_not_called()

    @patch("cjwstate.rabbitmq.queue_render")
    @patch("renderer.execute.execute_workflow")
    def test_render_unneeded_execution_so_requeue(self, mock_execute, queue_render):
        mock_execute.side_effect = async_err(execute.UnneededExecution)
        queue_render.side_effect = async_noop
        workflow = Workflow.objects.create(last_delta_id=123)

        async def inner():
            with self.assertLogs("renderer", level="INFO") as cm:
                await render_workflow_and_maybe_requeue(
                    SuccessfulRenderLocker(), workflow.id, 123
                )
                self.assertRegex(
                    cm.output[0],
                    r"^INFO:renderer.render:Start execute_workflow\(\d+, \d+\)",
                )
                self.assertRegex(
                    cm.output[1],
                    r"^INFO:renderer.render:End execute_workflow\(\d+, \d+\)",
                )
                self.assertRegex(
                    cm.output[2],
                    r"^INFO:renderer.render:UnneededExecution in execute_workflow\(\d+, \d+\)$",
                )

        self.run_with_async_db(inner())
        queue_render.assert_called_with(workflow.id, 123)
