from unittest.mock import patch

from cjwmodule.arrow.testing import make_column, make_table

from cjwkernel.types import RenderResult
from cjwstate import clientside, commands, rabbitmq
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.models import Workflow
from cjwstate.models.commands import DuplicateTab
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class DuplicateTabTest(DbTestCase):
    @patch.object(rabbitmq, "queue_render")
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_duplicate_empty_tab(self, send_update, queue_render):
        send_update.side_effect = async_noop
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()

        cmd = self.run_with_async_db(
            commands.do(
                DuplicateTab,
                workflow_id=workflow.id,
                from_tab=tab,
                slug="tab-2",
                name="Tab 2",
            )
        )

        # Adds new tab
        cmd.tab.refresh_from_db()
        self.assertFalse(cmd.tab.is_deleted)
        self.assertEqual(cmd.tab.slug, "tab-2")
        self.assertEqual(cmd.tab.name, "Tab 2")
        workflow.refresh_from_db()
        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                workflow=clientside.WorkflowUpdate(
                    updated_at=workflow.updated_at, tab_slugs=["tab-1", "tab-2"]
                ),
                tabs={
                    "tab-2": clientside.TabUpdate(
                        slug="tab-2",
                        name="Tab 2",
                        step_ids=[],
                        selected_step_index=None,
                    )
                },
            ),
        )

        # Backward: should delete tab
        self.run_with_async_db(commands.undo(workflow.id))
        cmd.tab.refresh_from_db()
        self.assertTrue(cmd.tab.is_deleted)
        workflow.refresh_from_db()
        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                workflow=clientside.WorkflowUpdate(
                    updated_at=workflow.updated_at, tab_slugs=["tab-1"]
                ),
                clear_tab_slugs=frozenset(["tab-2"]),
            ),
        )

        # Forward: should bring us back
        self.run_with_async_db(commands.redo(workflow.id))
        cmd.tab.refresh_from_db()
        self.assertFalse(cmd.tab.is_deleted)
        workflow.refresh_from_db()
        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                workflow=clientside.WorkflowUpdate(
                    updated_at=workflow.updated_at, tab_slugs=["tab-1", "tab-2"]
                ),
                tabs={
                    "tab-2": clientside.TabUpdate(
                        slug="tab-2",
                        name="Tab 2",
                        step_ids=[],
                        selected_step_index=None,
                    )
                },
            ),
        )

        # There should never be a render: we aren't changing any module
        # outputs.
        queue_render.assert_not_called()

    @patch.object(rabbitmq, "queue_render")
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_duplicate_nonempty_unrendered_tab(self, send_update, queue_render):
        send_update.side_effect = async_noop
        queue_render.side_effect = async_noop
        workflow = Workflow.create_and_init()
        init_delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        tab.selected_step_position = 1
        tab.save(update_fields=["selected_step_position"])
        # step1 and step2 have not yet been rendered. (But while we're
        # duplicating, conceivably a render could be running; so when we
        # duplicate them, we need to queue a render.)
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            params={"p": "s1"},
            last_relevant_delta_id=init_delta_id,
        )
        tab.steps.create(
            order=1,
            slug="step-2",
            module_id_name="y",
            params={"p": "s2"},
            last_relevant_delta_id=init_delta_id,
        )

        cmd = self.run_with_async_db(
            commands.do(
                DuplicateTab,
                workflow_id=workflow.id,
                from_tab=tab,
                slug="tab-2",
                name="Tab 2",
            )
        )

        # Adds new tab
        cmd.tab.refresh_from_db()
        [step1dup, step2dup] = list(cmd.tab.live_steps.all())
        self.assertFalse(cmd.tab.is_deleted)
        self.assertEqual(cmd.tab.slug, "tab-2")
        self.assertEqual(cmd.tab.name, "Tab 2")
        self.assertEqual(cmd.tab.selected_step_position, 1)
        self.assertEqual(step1dup.order, 0)
        self.assertEqual(step1dup.module_id_name, "x")
        self.assertEqual(step1dup.params, {"p": "s1"})
        self.assertEqual(
            step1dup.last_relevant_delta_id,
            # `cmd.id` would be intuitive, but that would be hard
            # to implement (and we assume we don't need to).
            # (Duplicate also duplicates _cache values_, which
            # means it's expensive to tweak step1's delta ID.)
            step1.last_relevant_delta_id,
        )
        self.assertEqual(step2dup.order, 1)
        self.assertEqual(step2dup.module_id_name, "y")
        self.assertEqual(step2dup.params, {"p": "s2"})
        self.assertNotEqual(step1dup.id, step1.id)
        delta = send_update.mock_calls[0][1][1]
        self.assertEqual(delta.tabs["tab-2"].step_ids, [step1dup.id, step2dup.id])
        self.assertEqual(set(delta.steps.keys()), set([step1dup.id, step2dup.id]))
        step1update = delta.steps[step1dup.id]
        self.assertEqual(
            step1update.last_relevant_delta_id, step1.last_relevant_delta_id
        )
        # We should call render: we don't know whether there's a render queued;
        # and these new steps are in need of render.
        queue_render.assert_called_with(workflow.id, cmd.id)
        queue_render.reset_mock()  # so we can assert next time

        # undo
        self.run_with_async_db(commands.undo(workflow.id))
        cmd.tab.refresh_from_db()
        self.assertTrue(cmd.tab.is_deleted)
        delta = send_update.mock_calls[1][1][1]
        self.assertEqual(delta.clear_tab_slugs, frozenset(["tab-2"]))
        self.assertEqual(delta.clear_step_ids, frozenset([step1dup.id, step2dup.id]))
        # No need to call render(): these modules can't possibly have changed,
        # and nobody cares what's in their cache.
        queue_render.assert_not_called()

        # redo
        self.run_with_async_db(commands.redo(workflow.id))
        # Need to call render() again -- these modules are still out-of-date
        queue_render.assert_called_with(workflow.id, cmd.id)

    @patch.object(rabbitmq, "queue_render")
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_duplicate_nonempty_rendered_tab(self, send_update, queue_render):
        send_update.side_effect = async_noop
        queue_render.side_effect = async_noop
        workflow = Workflow.create_and_init()
        init_delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        # step1 and step2 have not yet been rendered. (But while we're
        # duplicating, conceivably a render could be running; so when we
        # duplicate them, we need to queue a render.)
        step1 = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            params={"p": "s1"},
            last_relevant_delta_id=init_delta_id,
        )
        write_to_rendercache(
            workflow, step1, init_delta_id, make_table(make_column("A", [1]))
        )

        cmd = self.run_with_async_db(
            commands.do(
                DuplicateTab,
                workflow_id=workflow.id,
                from_tab=tab,
                slug="tab-2",
                name="Tab 2",
            )
        )
        tab2 = workflow.tabs.last()
        self.assertNotEqual(tab2.id, tab.id)
        step2 = tab2.steps.last()
        # We need to render: render() in Steps in the second Tab will be called
        # with different `tab_name` than in the first Tab, meaning their output
        # may be different.
        self.assertIsNone(step2.cached_render_result)
        queue_render.assert_called_with(workflow.id, cmd.id)

    def test_tab_name_conflict_is_valueerror(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        with self.assertRaisesRegex(ValueError, "used"):
            self.run_with_async_db(
                commands.do(
                    DuplicateTab,
                    workflow_id=workflow.id,
                    from_tab=tab,
                    slug=tab.slug,
                    name="Tab 2",
                )
            )

    @patch.object(rabbitmq, "queue_render", async_noop)
    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_position_after_tab(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1, slug="tab-2", name="Tab 2")
        self.run_with_async_db(
            commands.do(
                DuplicateTab,
                workflow_id=workflow.id,
                from_tab=tab1,
                slug="tab-3",
                name="Tab 3",
            )
        )
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", flat=True)),
            ["tab-1", "tab-3", "tab-2"],
        )
