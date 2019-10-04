import asyncio
from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import AddTabCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class AddTabCommandTest(DbTestCase):
    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_append_tab(self):
        workflow = Workflow.create_and_init(selected_tab_position=0)
        cmd = self.run_with_async_db(
            commands.do(AddTabCommand, workflow=workflow, slug="tab-2", name="A")
        )
        new_tab = workflow.live_tabs.get(position=1)
        self.assertEqual(new_tab.name, "A")
        self.assertEqual(new_tab.slug, "tab-2")
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-2", 1)],
        )

        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")), [("tab-1", 0)]
        )

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    def test_no_hard_or_soft_delete_when_deleting_applied_delta(self):
        workflow = Workflow.create_and_init()
        cmd = self.run_with_async_db(
            commands.do(AddTabCommand, workflow=workflow, slug="tab-2", name="A")
        )
        cmd.delete()
        self.assertEquals(workflow.live_tabs.count(), 2)

    @patch("server.websockets.ws_client_send_delta_async")
    def test_ws_data(self, send_delta):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_delta.return_value = future_none

        workflow = Workflow.create_and_init(selected_tab_position=0)
        cmd = self.run_with_async_db(
            commands.do(AddTabCommand, workflow=workflow, slug="tab-2", name="A")
        )
        delta1 = send_delta.call_args[0][1]
        self.assertEqual(delta1["updateWorkflow"]["tab_slugs"], ["tab-1", "tab-2"])
        self.assertEqual(list(delta1["updateTabs"].keys()), ["tab-2"])
        with self.assertRaises(KeyError):
            delta1["clearTabIds"]

        self.run_with_async_db(commands.undo(cmd))
        delta2 = send_delta.call_args[0][1]
        self.assertEqual(delta2["updateWorkflow"]["tab_slugs"], ["tab-1"])
        with self.assertRaises(KeyError):
            delta2["updateTabs"]
        self.assertEqual(delta2["clearTabSlugs"], ["tab-2"])
