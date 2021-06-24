import asyncio
import datetime
from unittest.mock import patch

from dateutil.parser import isoparse

from cjwstate import commands, rabbitmq
from cjwstate.models.commands import SetStepDataVersion
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


@patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
class SetStepParamsTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.create_and_init()
        self.step = self.workflow.tabs.first().steps.create(
            order=0, slug="step-1", last_relevant_delta_id=self.workflow.last_delta_id
        )

    def _store_fetched_table(self, stored_at=None) -> datetime.datetime:
        if stored_at is None:
            stored_at = datetime.datetime.now()
        self.step.stored_objects.create(key="fake", size=10, stored_at=stored_at)
        return stored_at

    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening", async_noop)
    def test_change_data_version(self):
        # Create two data versions, use the second
        date1 = self._store_fetched_table(stored_at=datetime.datetime(2021, 6, 24))
        date2 = self._store_fetched_table(stored_at=datetime.datetime(2021, 6, 23))

        self.step.stored_data_version = date2
        self.step.save(update_fields=["stored_data_version"])

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Change back to first version
        cmd = self.run_with_async_db(
            commands.do(
                SetStepDataVersion,
                workflow_id=self.workflow.id,
                step=self.step,
                new_version=isoparse("2021-06-24T00:00:00.000000Z"),
            )
        )
        self.assertEqual(self.step.stored_data_version, date1)

        self.workflow.refresh_from_db()
        v2 = cmd.id
        # workflow revision should have been incremented
        self.step.refresh_from_db()
        self.assertEqual(self.step.last_relevant_delta_id, v2)

        # undo
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.step.refresh_from_db()
        self.assertEqual(self.step.last_relevant_delta_id, v1)
        self.assertEqual(self.step.stored_data_version, date2)

        # redo
        self.run_with_async_db(commands.redo(self.workflow.id))
        self.step.refresh_from_db()
        self.assertEqual(self.step.last_relevant_delta_id, v2)
        self.assertEqual(self.step.stored_data_version, date1)

    @patch.object(rabbitmq, "queue_render")
    def test_change_version_queue_render_if_notifying(self, queue_render):
        queue_render.return_value = future_none

        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.step.notifications = True
        self.step.stored_data_version = date1
        self.step.save()

        delta = self.run_with_async_db(
            commands.do(
                SetStepDataVersion,
                workflow_id=self.workflow.id,
                step=self.step,
                new_version=date2,
            )
        )

        queue_render.assert_called_with(self.step.workflow_id, delta.id)

    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_accept_deleted_version(self):
        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.step.notifications = False
        self.step.stored_data_version = date1
        self.step.save()

        delta = self.run_with_async_db(
            commands.do(
                SetStepDataVersion,
                workflow_id=self.workflow.id,
                step=self.step,
                new_version=date2,
            )
        )

        self.step.stored_objects.get(stored_at=date1).delete()

        self.run_with_async_db(commands.undo(self.workflow.id))
        self.step.refresh_from_db()
        self.assertEqual(self.step.stored_data_version, date1)

        self.run_with_async_db(commands.redo(self.workflow.id))
        self.step.refresh_from_db()
        self.assertEqual(self.step.stored_data_version, date2)

    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening")
    @patch.object(rabbitmq, "queue_render")
    def test_change_version_queue_render_if_listening_and_no_notification(
        self, queue_render, queue_render_if_listening
    ):
        queue_render_if_listening.return_value = future_none

        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.step.notifications = False
        self.step.stored_data_version = date1
        self.step.save()

        delta = self.run_with_async_db(
            commands.do(
                SetStepDataVersion,
                workflow_id=self.workflow.id,
                step=self.step,
                new_version=date2,
            )
        )

        queue_render.assert_not_called()
        queue_render_if_listening.assert_called_with(self.step.workflow_id, delta.id)
