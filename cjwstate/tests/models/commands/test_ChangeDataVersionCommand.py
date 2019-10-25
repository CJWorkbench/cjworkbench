import asyncio
from unittest.mock import patch
from django.utils import timezone
from cjwstate import commands, minio
from cjwstate.models import Workflow
from cjwstate.models.commands import ChangeDataVersionCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


@patch.object(commands, "websockets_notify", async_noop)
class ChangeDataVersionCommandTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.create_and_init()
        self.wf_module = self.workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.workflow.last_delta_id
        )

    def _store_fetched_table(self) -> timezone.datetime:
        return self.wf_module.stored_objects.create(
            key="fake", bucket=minio.StoredObjectsBucket, size=10
        ).stored_at

    @patch("server.websockets.queue_render_if_listening", async_noop)
    def test_change_data_version(self):
        # Create two data versions, use the second
        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.wf_module.stored_data_version = date2
        self.wf_module.save()

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Change back to first version
        cmd = self.run_with_async_db(
            commands.do(
                ChangeDataVersionCommand,
                workflow_id=self.workflow.id,
                wf_module=self.wf_module,
                new_version=date1,
            )
        )
        self.assertEqual(self.wf_module.stored_data_version, date1)

        self.workflow.refresh_from_db()
        v2 = cmd.id
        # workflow revision should have been incremented
        self.assertEqual(self.wf_module.last_relevant_delta_id, v2)

        # undo
        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(self.wf_module.last_relevant_delta_id, v1)
        self.assertEqual(self.wf_module.stored_data_version, date2)

        # redo
        self.run_with_async_db(commands.redo(cmd))
        self.assertEqual(self.wf_module.last_relevant_delta_id, v2)
        self.assertEqual(self.wf_module.stored_data_version, date1)

    @patch("server.rabbitmq.queue_render")
    def test_change_version_queue_render_if_notifying(self, queue_render):
        queue_render.return_value = future_none

        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.wf_module.notifications = True
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            commands.do(
                ChangeDataVersionCommand,
                workflow_id=self.workflow.id,
                wf_module=self.wf_module,
                new_version=date2,
            )
        )

        queue_render.assert_called_with(self.wf_module.workflow_id, delta.id)

    @patch("server.websockets.queue_render_if_listening", async_noop)
    @patch("server.rabbitmq.queue_render", async_noop)
    def test_accept_deleted_version(self):
        """
        Let the user choose whichever version is desired, even if it does not
        exist.

        The errors will be user-visible ... _later_.
        """
        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            commands.do(
                ChangeDataVersionCommand,
                workflow_id=self.workflow.id,
                wf_module=self.wf_module,
                new_version=date2,
            )
        )

        self.wf_module.stored_objects.get(stored_at=date1).delete()

        self.run_with_async_db(commands.undo(delta))
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date1)

        self.run_with_async_db(commands.redo(delta))
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date2)

    @patch("server.websockets.queue_render_if_listening")
    @patch("server.rabbitmq.queue_render")
    def test_change_version_queue_render_if_listening_and_no_notification(
        self, queue_render, queue_render_if_listening
    ):
        queue_render_if_listening.return_value = future_none

        date1 = self._store_fetched_table()
        date2 = self._store_fetched_table()

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            commands.do(
                ChangeDataVersionCommand,
                workflow_id=self.workflow.id,
                wf_module=self.wf_module,
                new_version=date2,
            )
        )

        queue_render.assert_not_called()
        queue_render_if_listening.assert_called_with(
            self.wf_module.workflow_id, delta.id
        )
