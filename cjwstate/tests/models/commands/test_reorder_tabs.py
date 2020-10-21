from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import ReorderTabs
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class MockLoadedModule:
    def __init__(self, *args, **kwargs):
        pass

    def migrate_params(self, params):
        return params  # no-op


class ReorderTabsTest(DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(commands, "websockets_notify", async_noop)
    @patch.object(commands, "queue_render", async_noop)
    def test_reorder_slugs(self):
        workflow = Workflow.create_and_init()  # tab slug: tab-1
        workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderTabs,
                workflow_id=workflow.id,
                new_order=["tab-3", "tab-1", "tab-2"],
            )
        )
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-3", 0), ("tab-1", 1), ("tab-2", 2)],
        )

        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-1", 0), ("tab-2", 1), ("tab-3", 2)],
        )

        self.run_with_async_db(commands.redo(cmd))
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", "position")),
            [("tab-3", 0), ("tab-1", 1), ("tab-2", 2)],
        )

    @patch.object(commands, "websockets_notify", async_noop)
    @patch.object(commands, "queue_render", async_noop)
    def test_adjust_selected_tab_position(self):
        # tab slug: tab-1
        workflow = Workflow.create_and_init(selected_tab_position=2)
        workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderTabs,
                workflow_id=workflow.id,
                new_order=["tab-3", "tab-1", "tab-2"],
            )
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

        self.run_with_async_db(commands.undo(cmd))
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 2)

        self.run_with_async_db(commands.redo(cmd))
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch.object(commands, "websockets_notify", async_noop)
    @patch.object(commands, "queue_render", async_noop)
    def test_change_dependent_steps(self):
        # tab slug: tab-1
        workflow = Workflow.create_and_init(selected_tab_position=2)
        workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        # Create `step` depending on tabs 2+3 (and their order)
        module_zipfile = create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "tabs", "type": "multitab"}]}
        )
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            params={"tabs": ["tab-2", "tab-3"]},
            last_relevant_delta_id=workflow.last_delta_id,
            cached_migrated_params={"tabs": ["tab-2", "tab-3"]},
            cached_migrated_params_module_version=module_zipfile.version,
        )

        cmd = self.run_with_async_db(
            commands.do(
                ReorderTabs,
                workflow_id=workflow.id,
                new_order=["tab-3", "tab-1", "tab-2"],
            )
        )
        step.refresh_from_db()
        self.assertEqual(step.last_relevant_delta_id, cmd.id)

    @patch.object(commands, "websockets_notify")
    @patch.object(commands, "queue_render", async_noop)
    def test_clientside_update(self, send_delta):
        send_delta.side_effect = async_noop

        # initial tab slug: tab-1
        workflow = Workflow.create_and_init(selected_tab_position=2)
        workflow.tabs.create(position=1, slug="tab-2")
        workflow.tabs.create(position=2, slug="tab-3")

        self.run_with_async_db(
            commands.do(
                ReorderTabs,
                workflow_id=workflow.id,
                new_order=["tab-3", "tab-1", "tab-2"],
            )
        )

        delta = send_delta.call_args[0][1]
        self.assertEqual(delta.workflow.tab_slugs, ["tab-3", "tab-1", "tab-2"])

    def test_disallow_duplicate_tab_slug(self):
        workflow = Workflow.create_and_init()  # tab 1 slug: tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderTabs,
                    workflow_id=workflow.id,
                    new_order=["tab-1", "tab-1", "tab-2"],
                )
            )

    def test_disallow_missing_tab_slug(self):
        workflow = Workflow.create_and_init()  # initial tab slug: tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(ReorderTabs, workflow_id=workflow.id, new_order=["tab-1"])
            )

    def test_no_op(self):
        workflow = Workflow.create_and_init()  # initial tab slug: tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderTabs,
                workflow_id=workflow.id,
                new_order=["tab-1", "tab-2"],
            )
        )
        self.assertIsNone(cmd)
