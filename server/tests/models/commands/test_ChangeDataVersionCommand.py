import asyncio
from unittest.mock import patch
import pandas as pd
from server.models import Workflow
from server.models.commands import ChangeDataVersionCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


@patch("server.models.Delta.ws_notify", async_noop)
class ChangeDataVersionCommandTests(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.create_and_init()
        self.wf_module = self.workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.workflow.last_delta_id
        )

    @patch("server.websockets.queue_render_if_listening", async_noop)
    def test_change_data_version(self):
        # Create two data versions, use the second
        date1 = self.wf_module.store_fetched_table(pd.DataFrame({"A": [1]}))
        date2 = self.wf_module.store_fetched_table(pd.DataFrame({"A": [2]}))

        self.wf_module.stored_data_version = date2
        self.wf_module.save()

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Change back to first version
        cmd = self.run_with_async_db(
            ChangeDataVersionCommand.create(
                workflow=self.workflow, wf_module=self.wf_module, new_version=date1
            )
        )
        self.assertEqual(self.wf_module.stored_data_version, date1)

        self.workflow.refresh_from_db()
        v2 = cmd.id
        # workflow revision should have been incremented
        self.assertEqual(self.wf_module.last_relevant_delta_id, v2)

        # undo
        self.run_with_async_db(cmd.backward())
        self.assertEqual(self.wf_module.last_relevant_delta_id, v1)
        self.assertEqual(self.wf_module.stored_data_version, date2)

        # redo
        self.run_with_async_db(cmd.forward())
        self.assertEqual(self.wf_module.last_relevant_delta_id, v2)
        self.assertEqual(self.wf_module.stored_data_version, date1)

    @patch("server.rabbitmq.queue_render")
    def test_change_version_queue_render_if_notifying(self, queue_render):
        queue_render.return_value = future_none

        df1 = pd.DataFrame({"A": [1]})
        df2 = pd.DataFrame({"B": [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = True
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            ChangeDataVersionCommand.create(
                workflow=self.workflow, wf_module=self.wf_module, new_version=date2
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
        df1 = pd.DataFrame({"A": [1]})
        df2 = pd.DataFrame({"B": [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            ChangeDataVersionCommand.create(
                workflow=self.workflow, wf_module=self.wf_module, new_version=date2
            )
        )

        self.wf_module.stored_objects.get(stored_at=date1).delete()

        self.run_with_async_db(delta.backward())
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date1)

        self.run_with_async_db(delta.forward())
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date2)

    @patch("server.websockets.queue_render_if_listening")
    @patch("server.rabbitmq.queue_render")
    def test_change_version_queue_render_if_listening_and_no_notification(
        self, queue_render, queue_render_if_listening
    ):
        queue_render_if_listening.return_value = future_none

        df1 = pd.DataFrame({"A": [1]})
        df2 = pd.DataFrame({"B": [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = self.run_with_async_db(
            ChangeDataVersionCommand.create(
                workflow=self.workflow, wf_module=self.wf_module, new_version=date2
            )
        )

        queue_render.assert_not_called()
        queue_render_if_listening.assert_called_with(
            self.wf_module.workflow_id, delta.id
        )
