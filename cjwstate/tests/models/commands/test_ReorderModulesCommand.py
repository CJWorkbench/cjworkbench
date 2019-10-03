from unittest.mock import patch
from cjwstate.models import Workflow
from cjwstate.models.commands import InitWorkflowCommand, ReorderModulesCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch("server.rabbitmq.queue_render", async_noop)
@patch("cjwstate.models.Delta.ws_notify", async_noop)
class ReorderModulesCommandTest(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0, slug="tab-1")

    def assertWfModuleVersions(self, expected_versions):
        positions = list(self.tab.live_wf_modules.values_list("order", flat=True))
        self.assertEqual(positions, list(range(0, len(expected_versions))))

        versions = list(
            self.tab.live_wf_modules.values_list("last_relevant_delta_id", flat=True)
        )
        self.assertEqual(versions, expected_versions)

    def test_reorder_modules(self):
        all_modules = self.tab.live_wf_modules
        v1 = self.delta.id

        wfm1 = self.tab.wf_modules.create(
            last_relevant_delta_id=v1, order=0, slug="step-1"
        )
        wfm2 = self.tab.wf_modules.create(
            last_relevant_delta_id=v1, order=1, slug="step-2"
        )
        wfm3 = self.tab.wf_modules.create(
            last_relevant_delta_id=v1, order=2, slug="step-3"
        )

        cmd = self.run_with_async_db(
            ReorderModulesCommand.create(
                workflow=self.workflow,
                tab=self.tab,
                new_order=[wfm1.id, wfm3.id, wfm2.id],
            )
        )
        v2 = cmd.id
        self.assertWfModuleVersions([v1, v2, v2])
        wfm2.refresh_from_db()
        wfm3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)), [wfm1.id, wfm3.id, wfm2.id]
        )

        # undo
        self.run_with_async_db(cmd.backward())
        self.assertWfModuleVersions([v1, v1, v1])
        wfm2.refresh_from_db()
        wfm3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)), [wfm1.id, wfm2.id, wfm3.id]
        )

        # redo
        self.run_with_async_db(cmd.forward())
        self.assertWfModuleVersions([v1, v2, v2])
        wfm2.refresh_from_db()
        wfm3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)), [wfm1.id, wfm3.id, wfm2.id]
        )

    def test_reorder_modules_reject_other_tabs(self):
        """
        User cannot game the system: only one tab is allowed.

        (A user should not be able to affect WfModules outside of his/her
        workflow. There's nothing in the architecture that could lead us there,
        but let's be absolutely sure by testing.)
        """
        v1 = self.delta.id
        wfm1 = self.tab.wf_modules.create(
            last_relevant_delta_id=v1, order=0, slug="step-1"
        )
        wfm2 = self.tab.wf_modules.create(
            last_relevant_delta_id=v1, order=1, slug="step-2"
        )

        tab2 = self.workflow.tabs.create(position=1, slug="tab-2")
        wfm3 = tab2.wf_modules.create(last_relevant_delta_id=v1, order=2, slug="step-3")

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                ReorderModulesCommand.create(
                    workflow=self.workflow,
                    tab=self.tab,
                    new_order=[wfm1.id, wfm3.id, wfm2.id],
                )
            )

    def test_missing_wf_module_valueerror(self):
        wfm1 = self.tab.wf_modules.create(
            last_relevant_delta_id=self.delta.id, order=0, slug="step-1"
        )
        with self.assertRaises(ValueError):
            self.run_with_async_db(
                ReorderModulesCommand.create(
                    workflow=self.workflow, tab=self.tab, new_order=[wfm1.id + 1]
                )
            )

    def test_non_array_valueerror(self):
        with self.assertRaises(ValueError):
            self.run_with_async_db(
                ReorderModulesCommand.create(
                    workflow=self.workflow, tab=self.tab, new_order={"not": "an array"}
                )
            )

    def test_not_enough_wfmodules_valueerror(self):
        wfm1 = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        self.tab.wf_modules.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                ReorderModulesCommand.create(
                    workflow=self.workflow, tab=self.tab, new_order=[wfm1.id]
                )
            )

    def test_repeated_wfmodules_valueerror(self):
        wfm1 = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        self.tab.wf_modules.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                ReorderModulesCommand.create(
                    workflow=self.workflow, tab=self.tab, new_order=[wfm1.id, wfm1.id]
                )
            )

    def test_no_change_does_nothing(self):
        wfm1 = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        wfm2 = self.tab.wf_modules.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        cmd = self.run_with_async_db(
            ReorderModulesCommand.create(
                workflow=self.workflow, tab=self.tab, new_order=[wfm1.id, wfm2.id]
            )
        )
        self.assertIsNone(cmd)
