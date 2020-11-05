import asyncio
from unittest.mock import patch

from cjwstate import clientside, commands
from cjwstate.models import Workflow
from cjwstate.models.commands import ReorderBlocks
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class AddBlockTest(DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(commands, "websockets_notify", async_noop)
    def test_value_error_on_wrong_slugs(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="1"
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderBlocks,
                    workflow_id=workflow.id,
                    slugs=["block-2", "block-3", "block-1"],
                )
            )

    @patch.object(commands, "websockets_notify", async_noop)
    def test_none_on_no_change(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="1"
        )

        cmd = self.run_with_async_db(
            commands.do(
                ReorderBlocks, workflow_id=workflow.id, slugs=["block-1", "block-2"]
            )
        )
        self.assertIsNone(cmd)

    @patch.object(commands, "websockets_notify")
    def test_reorder_blocks_on_custom_report(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=2, slug="block-3", block_type="Text", text_markdown="1"
        )

        cmd = self.run_with_async_db(
            commands.do(
                ReorderBlocks,
                workflow_id=workflow.id,
                slugs=["block-2", "block-3", "block-1"],
            )
        )
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-2", 0), ("block-3", 1), ("block-1", 2)],
        )
        delta1 = send_update.call_args[0][1]
        self.assertIsNone(delta1.workflow.has_custom_report)
        self.assertEqual(delta1.workflow.block_slugs, ["block-2", "block-3", "block-1"])

        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-1", 0), ("block-2", 1), ("block-3", 2)],
        )
        delta2 = send_update.call_args[0][1]
        self.assertIsNone(delta2.workflow.has_custom_report)
        self.assertEqual(delta2.workflow.block_slugs, ["block-1", "block-2", "block-3"])

    @patch.object(commands, "websockets_notify", async_noop)
    def test_value_error_on_wrong_auto_report_slugs(self):
        create_module_zipfile("chart", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab = workflow.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="nochart")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="chart")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="chart")

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderBlocks,
                    workflow_id=workflow.id,
                    slugs=["block-nope", "block-auto-step-2"],
                )
            )

    @patch.object(commands, "websockets_notify", async_noop)
    def test_none_on_no_auto_report_change(self):
        create_module_zipfile("chart", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab = workflow.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="nochart")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="chart")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="chart")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderBlocks,
                workflow_id=workflow.id,
                slugs=["block-auto-step-2", "block-auto-step-3"],
            )
        )
        self.assertIsNone(cmd)

    @patch.object(commands, "websockets_notify")
    def test_reorder_blocks_on_automatically_generated_report(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        create_module_zipfile("chart", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab = workflow.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="nochart")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="chart")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="chart")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderBlocks,
                workflow_id=workflow.id,
                slugs=["block-auto-step-3", "block-auto-step-2"],
            )
        )
        self.assertEqual(
            list(
                workflow.blocks.values_list(
                    "position", "slug", "block_type", "text_markdown", "step_id"
                )
            ),
            [
                (0, "block-auto-step-3", "Chart", "", step3.id),
                (1, "block-auto-step-2", "Chart", "", step2.id),
            ],
        )
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.workflow.has_custom_report, True)
        self.assertEqual(
            delta1.workflow.block_slugs,
            ["block-auto-step-3", "block-auto-step-2"],
        )
        self.assertEqual(
            delta1.blocks,
            {
                "block-auto-step-2": clientside.ChartBlock("step-2"),
                "block-auto-step-3": clientside.ChartBlock("step-3"),
            },
        )

        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(list(workflow.blocks.values_list("slug", "position")), [])
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.workflow.has_custom_report, False)
        self.assertEqual(delta2.workflow.block_slugs, [])
        self.assertEqual(
            delta2.clear_block_slugs,
            frozenset(["block-auto-step-2", "block-auto-step-3"]),
        )
        self.assertEqual(delta2.blocks, {})
