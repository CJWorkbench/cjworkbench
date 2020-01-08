import asyncio
from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import DeleteTabCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class DeleteTabCommandTest(DbTestCase):
    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_tab(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab2)
        )
        tab2.refresh_from_db()  # it is only _soft_-deleted.
        self.assertEqual(tab2.is_deleted, True)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-3", 1)],
        )

        self.run_with_async_db(commands.undo(cmd))
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, False)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-2", 1), ("tab-3", 2)],
        )

        self.run_with_async_db(commands.redo(cmd))
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, True)
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-3", 1)],
        )

    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_tab_before_selected_position_changes_position(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1)

        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab1)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

        self.run_with_async_db(commands.undo(cmd))
        workflow.refresh_from_db()
        # On un-delete, we select the un-deleted tab
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_tab_after_selected_position_ignores_position(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        workflow.tabs.create(position=1, slug="tab-2")
        tab3 = workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab3)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)

        self.run_with_async_db(commands.undo(cmd))
        workflow.refresh_from_db()
        # On un-delete, we select the un-deleted tab
        self.assertEqual(workflow.selected_tab_position, 2)

    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_last_tab(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab2 = workflow.tabs.create(position=1)

        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab2)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, True)

        self.run_with_async_db(commands.undo(cmd))
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)
        tab2.refresh_from_db()
        self.assertEqual(tab2.is_deleted, False)

    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_tab_0(self):
        workflow = Workflow.create_and_init(selected_tab_position=0)
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1)

        self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab1)
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch.object(commands, "websockets_notify", async_noop)
    def test_delete_last_tab_noop(self):
        workflow = Workflow.create_and_init(selected_tab_position=1)
        tab1 = workflow.tabs.first()

        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab1)
        )
        self.assertIsNone(cmd)

        tab1.refresh_from_db()
        self.assertEqual(tab1.is_deleted, False)

    @patch.object(commands, "websockets_notify")
    def test_clientside_update(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(selected_tab_position=0)  # tab-1
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        cmd = self.run_with_async_db(
            commands.do(DeleteTabCommand, workflow_id=workflow.id, tab=tab2)
        )
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.workflow.tab_slugs, ["tab-1"])
        self.assertFalse(delta1.tabs)
        self.assertEqual(delta1.clear_tab_slugs, frozenset(["tab-2"]))

        self.run_with_async_db(commands.undo(cmd))
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.workflow.tab_slugs, ["tab-1", "tab-2"])
        self.assertEqual(list(delta2.tabs.keys()), ["tab-2"])
        self.assertFalse(delta2.clear_tab_slugs)
