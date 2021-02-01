import asyncio
from unittest.mock import patch

from cjwstate import clientside, commands
from cjwstate.models.commands import DeleteBlock
from cjwstate.models.workflow import Workflow
from cjwstate.models.block import Block
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class DeleteBlockTest(DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(commands, "websockets_notify")
    def test_delete_block_from_custom_report(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="2"
        )
        workflow.blocks.create(
            position=2, slug="block-3", block_type="Text", text_markdown="3"
        )

        self.run_with_async_db(
            commands.do(DeleteBlock, workflow_id=workflow.id, slug="block-1")
        )
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-2", 0), ("block-3", 1)],
        )
        with self.assertRaises(Block.DoesNotExist):
            workflow.blocks.get(slug="block-1")
        block = workflow.blocks.get(slug="block-2")
        self.assertEqual(block.position, 0)
        delta1 = send_update.call_args[0][1]
        self.assertIsNone(delta1.workflow.has_custom_report)
        self.assertEqual(
            delta1.workflow.block_slugs,
            ["block-2", "block-3"],
        )
        self.assertEqual(delta1.blocks, {})
        self.assertEqual(delta1.clear_block_slugs, frozenset(["block-1"]))

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-1", 0), ("block-2", 1), ("block-3", 2)],
        )
        delta2 = send_update.call_args[0][1]
        self.assertIsNone(delta2.workflow.has_custom_report)
        self.assertEqual(delta2.workflow.block_slugs, ["block-1", "block-2", "block-3"])
        self.assertEqual(delta2.clear_block_slugs, frozenset({}))
        self.assertEqual(delta2.blocks, {"block-1": clientside.TextBlock("1")})

    @patch.object(commands, "websockets_notify")
    def test_delete_restore_chart_block(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)
        tab = workflow.tabs.first()
        step = tab.steps.create(order=0, slug="step-1")
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Chart", step_id=step.id
        )

        self.run_with_async_db(
            commands.do(DeleteBlock, workflow_id=workflow.id, slug="block-2")
        )
        self.run_with_async_db(commands.undo(workflow.id))

        self.assertEqual(
            list(
                workflow.blocks.values_list("slug", "position", "block_type", "step_id")
            ),
            [("block-1", 0, "Text", None), ("block-2", 1, "Chart", step.id)],
        )

    @patch.object(commands, "websockets_notify")
    def test_delete_restore_table_block(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)
        tab = workflow.tabs.first()
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="1"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Table", tab_id=tab.id
        )

        self.run_with_async_db(
            commands.do(DeleteBlock, workflow_id=workflow.id, slug="block-2")
        )
        self.run_with_async_db(commands.undo(workflow.id))

        self.assertEqual(
            list(
                workflow.blocks.values_list("slug", "position", "block_type", "tab_id")
            ),
            [("block-1", 0, "Text", None), ("block-2", 1, "Table", tab.id)],
        )

    @patch.object(commands, "websockets_notify")
    def test_delete_block_from_automatically_generated_report(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        create_module_zipfile("chart", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab = workflow.tabs.first()
        step1 = tab.steps.create(order=0, slug="step-1", module_id_name="nochart")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="chart")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="chart")

        self.run_with_async_db(
            commands.do(DeleteBlock, workflow_id=workflow.id, slug="block-auto-step-3")
        )
        self.assertEqual(
            list(
                workflow.blocks.values_list(
                    "position", "slug", "block_type", "text_markdown", "step_id"
                )
            ),
            [
                (0, "block-auto-step-2", "Chart", "", step2.id),
            ],
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.has_custom_report, True)
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.workflow.has_custom_report, True)
        self.assertEqual(delta1.workflow.block_slugs, ["block-auto-step-2"])
        self.assertEqual(
            delta1.blocks,
            {"block-auto-step-2": clientside.ChartBlock("step-2")},
        )

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(list(workflow.blocks.values_list("slug", "position")), [])
        workflow.refresh_from_db()
        self.assertEqual(workflow.has_custom_report, False)
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.workflow.has_custom_report, False)
        self.assertEqual(delta2.workflow.block_slugs, [])
        self.assertEqual(delta2.clear_block_slugs, frozenset(["block-auto-step-2"]))
        self.assertEqual(delta2.blocks, {})
