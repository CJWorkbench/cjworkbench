import asyncio
from contextlib import asynccontextmanager
import logging
from unittest.mock import patch
from dateutil import parser
from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase
from cron import autoupdate


future_none = asyncio.Future()
future_none.set_result(None)


class _RenderLock:
    def __init__(self):
        self.stalled = False

    async def stall_others(self):
        self.stalled = True


class SuccessfulRenderLock:
    @asynccontextmanager
    async def render_lock(self, workflow_id: int):
        lock = _RenderLock()
        try:
            yield lock
        finally:
            assert lock.stalled


class UpdatesTests(DbTestCase):
    @patch.object(rabbitmq, "queue_fetch")
    @patch.object(
        rabbitmq, "send_update_to_workflow_clients", lambda _1, _2: future_none
    )
    @patch("django.utils.timezone.now", lambda: parser.parse("Aug 28 1999 2:35PM UTC"))
    def test_queue_fetches(self, mock_queue_fetch):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)

        # step1 does not auto-update
        step1 = tab.steps.create(order=0, slug="step-1", auto_update_data=False)

        # step2 is ready to update
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            auto_update_data=True,
            last_update_check=parser.parse("Aug 28 1999 2:24PM UTC"),
            next_update=parser.parse("Aug 28 1999 2:34PM UTC"),
            update_interval=600,
        )

        # step3 has a few more minutes before it should update
        step3 = tab.steps.create(
            order=2,
            slug="step-3",
            auto_update_data=True,
            last_update_check=parser.parse("Aug 28 1999 2:20PM UTC"),
            next_update=parser.parse("Aug 28 1999 2:40PM UTC"),
            update_interval=1200,
        )

        mock_queue_fetch.return_value = future_none

        # eat log messages
        with self.assertLogs(autoupdate.__name__, logging.INFO):
            self.run_with_async_db(autoupdate.queue_fetches(SuccessfulRenderLock()))

        self.assertEqual(mock_queue_fetch.call_count, 1)
        mock_queue_fetch.assert_called_with(workflow.id, step2.id)

        step2.refresh_from_db()
        self.assertTrue(step2.is_busy)

        # Second call shouldn't fetch again, because it's busy
        self.run_with_async_db(autoupdate.queue_fetches(SuccessfulRenderLock()))

        self.assertEqual(mock_queue_fetch.call_count, 1)
