import asyncio
from unittest.mock import patch

from cjwstate import clientside, commands, rabbitmq
from cjwstate.models import Workflow, Block
from cjwstate.models.commands import ReplaceStep
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


class ReplaceStepTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_no_op_on_deleted_step(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab = workflow.tabs.first()
        tab.steps.create(
            order=0,
            slug="step-1",
            is_deleted=True,
            last_relevant_delta_id=workflow.last_delta_id,
            params={"foo": "bar"},
        )
        create_module_zipfile(
            "foo", spec_kwargs={"parameters": [dict(id_name="bar", type="string")]}
        )
        delta = self.run_with_async_db(
            commands.do(
                ReplaceStep,
                workflow_id=workflow.id,
                old_slug="step-1",
                slug="step-2",
                module_id_name="foo",
                param_values={"bar": "baz"},
            )
        )
        self.assertIsNone(delta)

    def test_key_error_on_missing_module_slug(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab = workflow.tabs.first()
        tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"foo": "bar"},
        )
        with self.assertRaises(KeyError):
            self.run_with_async_db(
                commands.do(
                    ReplaceStep,
                    workflow_id=workflow.id,
                    old_slug="step-1",
                    slug="step-2",
                    module_id_name="notfound",
                    param_values={},
                )
            )

    def test_value_error_on_invalid_param_values(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab = workflow.tabs.first()
        tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"foo": "bar"},
        )
        create_module_zipfile(
            "foo", spec_kwargs={"parameters": [dict(id_name="bar", type="string")]}
        )
        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReplaceStep,
                    workflow_id=workflow.id,
                    old_slug="step-1",
                    slug="step-2",
                    module_id_name="foo",
                    param_values={"bar": 3},
                )
            )

    @patch.object(commands, "websockets_notify", async_noop)
    @patch.object(rabbitmq, "queue_render")
    def test_replace_lone_step(self, queue_render):
        queue_render.side_effect = async_noop

        workflow = Workflow.create_and_init()  # tab-1
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )
        create_module_zipfile(
            "foo", spec_kwargs={"parameters": [dict(id_name="bar", type="string")]}
        )

        self.run_with_async_db(
            commands.do(
                ReplaceStep,
                workflow_id=workflow.id,
                old_slug="step-1",
                slug="step-2",
                module_id_name="foo",
                param_values={"bar": "baz"},
            )
        )
        queue_render.assert_called()
        step.refresh_from_db()  # it's only _soft_-deleted.
        step2 = tab.steps.get(slug="step-2")
        self.assertEqual(step.is_deleted, True)
        self.assertEqual(step2.is_deleted, False)
        self.assertEqual(step2.order, 0)
        self.assertEqual(step2.params, {"bar": "baz"})

        queue_render.reset_mock()
        self.run_with_async_db(commands.undo(workflow.id))
        queue_render.assert_called()
        step.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step.is_deleted, False)
        self.assertEqual(step2.is_deleted, True)

        queue_render.reset_mock()
        self.run_with_async_db(commands.redo(workflow.id))
        step.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step.is_deleted, True)
        self.assertEqual(step2.is_deleted, False)

    @patch.object(commands, "websockets_notify", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_param_value_defaults(self):
        workflow = Workflow.create_and_init()  # tab-1
        tab = workflow.tabs.first()
        tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )
        create_module_zipfile(
            "foo",
            spec_kwargs={
                "parameters": [dict(id_name="bar", type="string", default="DEFAULT")]
            },
        )
        delta = self.run_with_async_db(
            commands.do(
                ReplaceStep,
                workflow_id=workflow.id,
                old_slug="step-1",
                slug="step-2",
                module_id_name="foo",
                param_values={},
            )
        )

        self.assertEqual(delta.step2.params, {"bar": "DEFAULT"})

    @patch.object(commands, "websockets_notify")
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_clientside_updates(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        create_module_zipfile(
            "mod", spec_kwargs={"parameters": [dict(id_name="foo", type="string")]}
        )

        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"a": "A"},
        )
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"b": "B"},
        )
        step3 = tab.steps.create(
            order=2,
            slug="step-3",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"c": "C"},
        )

        delta = self.run_with_async_db(
            commands.do(
                ReplaceStep,
                workflow_id=workflow.id,
                old_slug="step-2",
                slug="step-2a",
                module_id_name="mod",
                param_values={"foo": "bar"},
            )
        )

        def assert_forward_update(update):
            self.assertEqual(update.clear_step_ids, frozenset([step2.id]))
            self.assertEqual(set(update.steps.keys()), {delta.step2_id, step3.id})
            self.assertEqual(update.steps[delta.step2_id], delta.step2.to_clientside())
            self.assertEqual(update.steps[step3.id].last_relevant_delta_id, delta.id)
            self.assertEqual(
                update.tabs,
                {
                    tab.slug: clientside.TabUpdate(
                        step_ids=[step1.id, delta.step2_id, step3.id]
                    )
                },
            )

        send_update.assert_called()
        assert_forward_update(send_update.call_args[0][1])

        self.run_with_async_db(commands.undo(workflow.id))
        update = send_update.call_args[0][1]
        self.assertEqual(update.clear_step_ids, frozenset([delta.step2_id]))
        self.assertEqual(set(update.steps.keys()), {step2.id, step3.id})
        self.assertEqual(
            update.steps[step2.id].last_relevant_delta_id, workflow.last_delta_id
        )
        self.assertEqual(
            update.steps[step3.id].last_relevant_delta_id, workflow.last_delta_id
        )
        self.assertEqual(
            update.tabs,
            {tab.slug: clientside.TabUpdate(step_ids=[step1.id, step2.id, step3.id])},
        )

        self.run_with_async_db(commands.redo(workflow.id))
        assert_forward_update(send_update.call_args[0][1])

    @patch.object(commands, "websockets_notify")
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_delete_custom_report_blocks(self, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)
        send_update.return_value = future_none

        create_module_zipfile(
            "mod", spec_kwargs={"parameters": [dict(id_name="bar", type="string")]}
        )

        workflow = Workflow.create_and_init(has_custom_report=True)  # tab-1
        tab = workflow.tabs.first()
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )
        step2 = tab.steps.create(
            order=1,
            slug="step-2",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )

        # Report will include the step twice, and have another step elsewhere
        # that should not be touched
        block1 = workflow.blocks.create(
            position=0, slug="block-step-1-1", block_type="Chart", step=step1
        )
        block2 = workflow.blocks.create(
            position=1, slug="block-step-2", block_type="Chart", step=step2
        )
        block3 = workflow.blocks.create(
            position=2, slug="block-step-1-2", block_type="Chart", step=step1
        )

        self.run_with_async_db(
            commands.do(
                ReplaceStep,
                workflow_id=workflow.id,
                old_slug="step-1",
                slug="step-3",
                module_id_name="mod",
                param_values={"bar": "baz"},
            )
        )

        with self.assertRaises(Block.DoesNotExist):
            block1.refresh_from_db()
        with self.assertRaises(Block.DoesNotExist):
            block3.refresh_from_db()
        block2.refresh_from_db()
        self.assertEqual(block2.position, 0)

        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(update.workflow.block_slugs, ["block-step-2"])
        self.assertEqual(update.blocks, {})

        self.run_with_async_db(commands.undo(workflow.id))
        # The old blocks are deleted. We expect new blocks with new IDs.
        with self.assertRaises(Block.DoesNotExist):
            block1.refresh_from_db()
        with self.assertRaises(Block.DoesNotExist):
            block3.refresh_from_db()
        new_block1 = workflow.blocks.get(slug=block1.slug)
        new_block3 = workflow.blocks.get(slug=block3.slug)
        self.assertEqual(new_block1.step_id, step1.id)
        self.assertEqual(new_block3.step_id, step1.id)
        block2.refresh_from_db()
        self.assertEqual(new_block1.position, 0)
        self.assertEqual(block2.position, 1)
        self.assertEqual(new_block3.position, 2)
        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(
            update.workflow.block_slugs,
            ["block-step-1-1", "block-step-2", "block-step-1-2"],
        )
        self.assertEqual(
            update.blocks,
            {
                "block-step-1-1": clientside.ChartBlock("step-1"),
                "block-step-1-2": clientside.ChartBlock("step-1"),
            },
        )

        self.run_with_async_db(commands.redo(workflow.id))
        block2.refresh_from_db()
        self.assertEqual(block2.position, 0)
