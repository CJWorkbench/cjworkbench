import asyncio
from unittest.mock import patch
from cjwstate import clientside, commands
from cjwstate.models import Workflow
from cjwstate.models.commands import AddTab
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class AddTabTest(DbTestCase):
    @patch.object(commands, "websockets_notify", async_noop)
    def test_append_tab(self):
        workflow = Workflow.create_and_init(selected_tab_position=0)
        self.run_with_async_db(
            commands.do(AddTab, workflow_id=workflow.id, slug="tab-2", name="A")
        )
        new_tab = workflow.live_tabs.get(position=1)
        self.assertEqual(new_tab.name, "A")
        self.assertEqual(new_tab.slug, "tab-2")
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-2", 1)],
        )

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")), [("tab-1", 0)]
        )

    @patch.object(commands, "websockets_notify", async_noop)
    def test_no_hard_or_soft_delete_when_deleting_applied_delta(self):
        workflow = Workflow.create_and_init()
        cmd = self.run_with_async_db(
            commands.do(AddTab, workflow_id=workflow.id, slug="tab-2", name="A")
        )
        cmd.delete()
        self.assertEquals(workflow.live_tabs.count(), 2)

    @patch.object(commands, "websockets_notify")
    def test_clientside_update(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(selected_tab_position=0)
        self.run_with_async_db(
            commands.do(AddTab, workflow_id=workflow.id, slug="tab-2", name="A")
        )
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.workflow.tab_slugs, ["tab-1", "tab-2"])
        self.assertEqual(list(delta1.tabs.keys()), ["tab-2"])
        self.assertEqual(delta1.clear_tab_slugs, frozenset())

        self.run_with_async_db(commands.undo(workflow.id))
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.workflow.tab_slugs, ["tab-1"])
        self.assertFalse(delta2.tabs)
        self.assertEqual(delta2.clear_tab_slugs, frozenset(["tab-2"]))
