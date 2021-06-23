import asyncio
from unittest.mock import patch

from cjwstate import clientside, commands, rabbitmq
from cjwstate.models.block import Block
from cjwstate.models.commands import SetBlockMarkdown
from cjwstate.models.workflow import Workflow
from cjworkbench.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class SetBlockMarkdownTest(DbTestCase):
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_set_block_markdown_happy_path(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        self.run_with_async_db(
            commands.do(
                SetBlockMarkdown,
                workflow_id=workflow.id,
                slug="block-1",
                markdown="bar",
            )
        )
        self.assertEqual(
            list(workflow.blocks.values_list("text_markdown", flat=True)), ["bar"]
        )
        delta1 = send_update.call_args[0][1]
        self.assertEqual(delta1.blocks, {"block-1": clientside.TextBlock("bar")})

        self.run_with_async_db(commands.undo(workflow.id))
        self.assertEqual(
            list(workflow.blocks.values_list("text_markdown", flat=True)), ["foo"]
        )
        delta2 = send_update.call_args[0][1]
        self.assertEqual(delta2.blocks, {"block-1": clientside.TextBlock("foo")})

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_block_markdown_empty_text_is_value_error(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    SetBlockMarkdown,
                    workflow_id=workflow.id,
                    slug="block-1",
                    markdown="",
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_block_markdown_same_text_is_no_op(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        cmd = self.run_with_async_db(
            commands.do(
                SetBlockMarkdown,
                workflow_id=workflow.id,
                slug="block-1",
                markdown="foo",
            )
        )
        self.assertIsNone(cmd)

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_block_markdown_missing_block_is_does_not_exist(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        with self.assertRaises(Block.DoesNotExist):
            self.run_with_async_db(
                commands.do(
                    SetBlockMarkdown,
                    workflow_id=workflow.id,
                    slug="block-2",
                    markdown="bar",
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_block_markdown_block_not_text_is_does_not_exist(self):
        workflow = Workflow.create_and_init(has_custom_report=True)
        tab = workflow.tabs.first()
        workflow.blocks.create(position=0, slug="block-1", block_type="Table", tab=tab)

        with self.assertRaises(Block.DoesNotExist):
            self.run_with_async_db(
                commands.do(
                    SetBlockMarkdown,
                    workflow_id=workflow.id,
                    slug="block-1",
                    markdown="bar",
                )
            )
