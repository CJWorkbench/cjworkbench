from unittest.mock import patch
from cjworkbench.types import ProcessResult
from server.models import Workflow
from server.models.commands import DuplicateTabCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class DuplicateTabCommandTest(DbTestCase):
    @patch("server.rabbitmq.queue_render")
    @patch("server.models.Delta.ws_notify")
    def test_duplicate_empty_tab(self, ws_notify, queue_render):
        ws_notify.side_effect = async_noop
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()

        cmd = self.run_with_async_db(
            DuplicateTabCommand.create(
                workflow=workflow, from_tab=tab, slug="tab-2", name="Tab 2"
            )
        )

        # Adds new tab
        cmd.tab.refresh_from_db()
        self.assertFalse(cmd.tab.is_deleted)
        self.assertEqual(cmd.tab.slug, "tab-2")
        self.assertEqual(cmd.tab.name, "Tab 2")
        ws_notify.assert_called_with(
            {
                "updateWorkflow": {
                    "name": workflow.name,
                    "public": False,
                    "last_update": cmd.datetime.isoformat(),
                    "tab_slugs": ["tab-1", "tab-2"],
                },
                "updateTabs": {
                    "tab-2": {
                        "slug": "tab-2",
                        "name": "Tab 2",
                        "wf_module_ids": [],
                        "selected_wf_module_position": None,
                    }
                },
                "updateWfModules": {},
            }
        )

        # Backward: should delete tab
        self.run_with_async_db(cmd.backward())
        cmd.tab.refresh_from_db()
        self.assertTrue(cmd.tab.is_deleted)
        ws_notify.assert_called_with(
            {
                "updateWorkflow": {
                    "name": workflow.name,
                    "public": False,
                    "last_update": workflow.last_delta.datetime.isoformat(),
                    "tab_slugs": ["tab-1"],
                },
                "clearTabSlugs": ["tab-2"],
                "clearWfModuleIds": [],
            }
        )

        # Forward: should bring us back
        self.run_with_async_db(cmd.forward())
        cmd.tab.refresh_from_db()
        self.assertFalse(cmd.tab.is_deleted)
        ws_notify.assert_called_with(
            {
                "updateWorkflow": {
                    "name": workflow.name,
                    "public": False,
                    "last_update": cmd.datetime.isoformat(),
                    "tab_slugs": ["tab-1", "tab-2"],
                },
                "updateTabs": {
                    "tab-2": {
                        "slug": "tab-2",
                        "name": "Tab 2",
                        "wf_module_ids": [],
                        "selected_wf_module_position": None,
                    }
                },
                "updateWfModules": {},
            }
        )

        # There should never be a render: we aren't changing any module
        # outputs.
        queue_render.assert_not_called()

    @patch("server.rabbitmq.queue_render")
    @patch("server.models.Delta.ws_notify")
    def test_duplicate_nonempty_unrendered_tab(self, ws_notify, queue_render):
        ws_notify.side_effect = async_noop
        queue_render.side_effect = async_noop
        workflow = Workflow.create_and_init()
        init_delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        tab.selected_wf_module_position = 1
        tab.save(update_fields=["selected_wf_module_position"])
        # wfm1 and wfm2 have not yet been rendered. (But while we're
        # duplicating, conceivably a render could be running; so when we
        # duplicate them, we need to queue a render.)
        wfm1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            params={"p": "s1"},
            last_relevant_delta_id=init_delta_id,
        )
        tab.wf_modules.create(
            order=1,
            slug="step-2",
            module_id_name="y",
            params={"p": "s2"},
            last_relevant_delta_id=init_delta_id,
        )

        cmd = self.run_with_async_db(
            DuplicateTabCommand.create(
                workflow=workflow, from_tab=tab, slug="tab-2", name="Tab 2"
            )
        )

        # Adds new tab
        cmd.tab.refresh_from_db()
        [wfm1dup, wfm2dup] = list(cmd.tab.live_wf_modules.all())
        self.assertFalse(cmd.tab.is_deleted)
        self.assertEqual(cmd.tab.slug, "tab-2")
        self.assertEqual(cmd.tab.name, "Tab 2")
        self.assertEqual(cmd.tab.selected_wf_module_position, 1)
        self.assertEqual(wfm1dup.order, 0)
        self.assertEqual(wfm1dup.module_id_name, "x")
        self.assertEqual(wfm1dup.params, {"p": "s1"})
        self.assertEqual(
            wfm1dup.last_relevant_delta_id,
            # `cmd.id` would be intuitive, but that would be hard
            # to implement (and we assume we don't need to).
            # (Duplicate also duplicates _cache values_, which
            # means it's expensive to tweak wfm1's delta ID.)
            wfm1.last_relevant_delta_id,
        )
        self.assertEqual(wfm2dup.order, 1)
        self.assertEqual(wfm2dup.module_id_name, "y")
        self.assertEqual(wfm2dup.params, {"p": "s2"})
        self.assertNotEqual(wfm1dup.id, wfm1.id)
        delta = ws_notify.mock_calls[0][1][0]
        self.assertEqual(
            delta["updateTabs"]["tab-2"]["wf_module_ids"], [wfm1dup.id, wfm2dup.id]
        )
        self.assertEqual(
            list(delta["updateWfModules"].keys()),
            # dict preserves order
            [str(wfm1dup.id), str(wfm2dup.id)],
        )
        wfm1update = delta["updateWfModules"][str(wfm1dup.id)]
        self.assertEqual(
            wfm1update["last_relevant_delta_id"], wfm1.last_relevant_delta_id
        )
        # We should call render: we don't know whether there's a render queued;
        # and these new steps are in need of render.
        queue_render.assert_called_with(workflow.id, cmd.id)
        queue_render.reset_mock()  # so we can assert next time

        # undo
        self.run_with_async_db(cmd.backward())
        cmd.tab.refresh_from_db()
        self.assertTrue(cmd.tab.is_deleted)
        delta = ws_notify.mock_calls[1][1][0]
        self.assertEqual(delta["clearTabSlugs"], ["tab-2"])
        self.assertEqual(
            delta["clearWfModuleIds"],
            # dict preserves order
            [str(wfm1dup.id), str(wfm2dup.id)],
        )
        # No need to call render(): these modules can't possibly have changed,
        # and nobody cares what's in their cache.
        queue_render.assert_not_called()

        # redo
        self.run_with_async_db(cmd.forward())
        # Need to call render() again -- these modules are still out-of-date
        queue_render.assert_called_with(workflow.id, cmd.id)

    @patch("server.rabbitmq.queue_render")
    @patch("server.models.Delta.ws_notify")
    def test_duplicate_nonempty_rendered_tab(self, ws_notify, queue_render):
        ws_notify.side_effect = async_noop
        workflow = Workflow.create_and_init()
        init_delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        # wfm1 and wfm2 have not yet been rendered. (But while we're
        # duplicating, conceivably a render could be running; so when we
        # duplicate them, we need to queue a render.)
        wfm1 = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            params={"p": "s1"},
            last_relevant_delta_id=init_delta_id,
        )
        wfm1.cache_render_result(init_delta_id, ProcessResult(error="simplest ctor"))

        self.run_with_async_db(
            DuplicateTabCommand.create(
                workflow=workflow, from_tab=tab, slug="tab-2", name="Tab 2"
            )
        )
        # No need to render: the result is already cached
        queue_render.assert_not_called()

    def test_tab_name_conflict_is_valueerror(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        with self.assertRaisesRegex(ValueError, "used"):
            self.run_with_async_db(
                DuplicateTabCommand.create(
                    workflow=workflow, from_tab=tab, slug=tab.slug, name="Tab 2"
                )
            )

    @patch("server.rabbitmq.queue_render", async_noop)
    @patch("server.models.Delta.ws_notify", async_noop)
    def test_position_after_tab(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1, slug="tab-2", name="Tab 2")
        self.run_with_async_db(
            DuplicateTabCommand.create(
                workflow=workflow, from_tab=tab1, slug="tab-3", name="Tab 3"
            )
        )
        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", flat=True)),
            ["tab-1", "tab-3", "tab-2"],
        )
