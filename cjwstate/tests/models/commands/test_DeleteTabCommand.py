import asyncio
from unittest.mock import patch
from cjwstate.models import Workflow
from cjwstate.models.commands import DeleteTabCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class DeleteTabCommandTest(DbTestCase):
    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_tab(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab2)
        )
        tab2.refresh_from_db()  # it is only _soft_-deleted.
        self.assertEqual(tab2.is_deleted, True)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-3", 1)],
        )

        self.run_with_async_db(cmd.backward())
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, False)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-2", 1), ("tab-3", 2)],
        )

        self.run_with_async_db(cmd.forward())
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, True)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-3", 1)],
        )

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_tab_before_selected_position_changes_position(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1)

        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab1)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

        self.run_with_async_db(cmd.backward())
        workflow.refresh_from_db()
        # On un-delete, we select the un-deleted tab
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_tab_after_selected_position_ignores_position(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        workflow.tabs.create(position=1, slug="tab-2")
        tab3 = workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab3)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)

        self.run_with_async_db(cmd.backward())
        workflow.refresh_from_db()
        # On un-delete, we select the un-deleted tab
        self.assertEqual(workflow.selected_tab_position, 2)

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_last_tab(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab2 = workflow.tabs.create(position=1)

        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab2)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, True)

        self.run_with_async_db(cmd.backward())
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, False)

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_tab_0(self):
        workflow = Workflow.create_and_init(selected_tab_position=0)
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1)

        self.run_with_async_db(DeleteTabCommand.create(workflow=workflow, tab=tab1))
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_delete_last_tab_noop(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab1 = workflow.tabs.first()

        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab1)
        )
        self.assertIsNone(cmd)

        tab1.refresh_from_db()
        self.assertEqual(tab1.is_deleted, False)

    @patch("server.websockets.ws_client_send_delta_async")
    def test_ws_data(self, send_delta):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_delta.return_value = future_none

        workflow = Workflow.create_and_init(selected_tab_position=0)  # tab-1
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        cmd = self.run_with_async_db(
            DeleteTabCommand.create(workflow=workflow, tab=tab2)
        )
        delta1 = send_delta.call_args[0][1]
        self.assertEqual(delta1["updateWorkflow"]["tab_slugs"], ["tab-1"])
        self.assertFalse("updateTabs" in delta1)
        self.assertEqual(delta1["clearTabSlugs"], ["tab-2"])

        self.run_with_async_db(cmd.backward())
        delta2 = send_delta.call_args[0][1]
        self.assertEqual(delta2["updateWorkflow"]["tab_slugs"], ["tab-1", "tab-2"])
        self.assertEqual(list(delta2["updateTabs"].keys()), ["tab-2"])
        self.assertFalse("clearTabSlugs" in delta2)
