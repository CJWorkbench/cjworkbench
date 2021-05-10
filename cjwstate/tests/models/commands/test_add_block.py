import asyncio
from unittest.mock import patch

from cjwstate import clientside, commands
from cjwstate.models import Workflow
from cjwstate.models.commands import AddBlock
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class AddBlockTest(DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(commands, "websockets_notify")
    def test_add_block_to_empty_workflow(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)

        self.run_with_async_db(
            commands.do(
                AddBlock,
                workflow_id=workflow.id,
                position=0,
                slug="block-1",
                block_type="Text",
                text_markdown="hi!",
            )
        )
        block = workflow.blocks.first()
        self.assertEqual(block.position, 0)
        self.assertEqual(block.slug, "block-1")
        self.assertEqual(block.text_markdown, "hi!")
        delta1 = send_update.call_args[0][1]
        self.assertIsNone(delta1.workflow.has_custom_report)
        self.assertEqual(delta1.workflow.block_slugs, ["block-1"])
        self.assertEqual(delta1.blocks, {"block-1": clientside.TextBlock("hi!")})

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(list(workflow.blocks.values_list("slug", "position")), [])
        delta2 = send_update.call_args[0][1]
        self.assertIsNone(delta2.workflow.has_custom_report)
        self.assertEqual(delta2.workflow.block_slugs, [])
        self.assertEqual(delta2.clear_block_slugs, frozenset(["block-1"]))
        self.assertEqual(delta2.blocks, {})

    @patch.object(commands, "websockets_notify")
    def test_add_block_to_custom_report(self, send_update):
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

        self.run_with_async_db(
            commands.do(
                AddBlock,
                workflow_id=workflow.id,
                position=1,
                slug="block-new",
                block_type="Text",
                text_markdown="hi!",
            )
        )
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-1", 0), ("block-new", 1), ("block-2", 2), ("block-3", 3)],
        )
        block = workflow.blocks.get(slug="block-new")
        self.assertEqual(block.position, 1)
        self.assertEqual(block.text_markdown, "hi!")
        delta1 = send_update.call_args[0][1]
        self.assertEqual(
            delta1.workflow.block_slugs,
            ["block-1", "block-new", "block-2", "block-3"],
        )
        self.assertEqual(delta1.blocks, {"block-new": clientside.TextBlock("hi!")})

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(
            list(workflow.blocks.values_list("slug", "position")),
            [("block-1", 0), ("block-2", 1), ("block-3", 2)],
        )
        delta2 = send_update.call_args[0][1]
        self.assertIsNone(delta2.workflow.has_custom_report)
        self.assertEqual(delta2.workflow.block_slugs, ["block-1", "block-2", "block-3"])
        self.assertEqual(delta2.clear_block_slugs, frozenset(["block-new"]))
        self.assertEqual(delta2.blocks, {})

    @patch.object(commands, "websockets_notify")
    def test_add_block_to_automatically_generated_report(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        create_module_zipfile("chart", spec_kwargs={"html_output": True})

        workflow = Workflow.create_and_init(has_custom_report=False)
        tab = workflow.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="nochart")
        step2 = tab.steps.create(order=1, slug="step-2", module_id_name="chart")
        step3 = tab.steps.create(order=2, slug="step-3", module_id_name="chart")

        self.run_with_async_db(
            commands.do(
                AddBlock,
                workflow_id=workflow.id,
                position=1,
                slug="block-1",
                block_type="Text",
                text_markdown="hi!",
            )
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.has_custom_report, True)
        self.assertEqual(
            list(
                workflow.blocks.values_list(
                    "position", "slug", "block_type", "text_markdown", "step_id"
                )
            ),
            [
                (0, "block-auto-step-2", "Chart", "", step2.id),
                (1, "block-1", "Text", "hi!", None),
                (2, "block-auto-step-3", "Chart", "", step3.id),
            ],
        )
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.workflow.has_custom_report, True)
        self.assertEqual(
            delta1.workflow.block_slugs,
            ["block-auto-step-2", "block-1", "block-auto-step-3"],
        )
        self.assertEqual(
            delta1.blocks,
            {
                "block-auto-step-2": clientside.ChartBlock("step-2"),
                "block-1": clientside.TextBlock("hi!"),
                "block-auto-step-3": clientside.ChartBlock("step-3"),
            },
        )

        self.run_with_async_db(commands.undo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.has_custom_report, False)
        self.assertEqual(list(workflow.blocks.values_list("slug", "position")), [])
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.workflow.has_custom_report, False)
        self.assertEqual(delta2.workflow.block_slugs, [])
        self.assertEqual(
            delta2.clear_block_slugs,
            frozenset(["block-auto-step-2", "block-1", "block-auto-step-3"]),
        )
        self.assertEqual(delta2.blocks, {})
