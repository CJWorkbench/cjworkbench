from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import InitWorkflow, ReorderSteps
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class ReorderStepsTest(DbTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflow.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0, slug="tab-1")

    def assertStepVersions(self, expected_versions):
        positions = list(self.tab.live_steps.values_list("order", flat=True))
        self.assertEqual(positions, list(range(0, len(expected_versions))))

        versions = list(
            self.tab.live_steps.values_list("last_relevant_delta_id", flat=True)
        )
        self.assertEqual(versions, expected_versions)

    def test_reorder_modules(self):
        all_modules = self.tab.live_steps
        v1 = self.delta.id

        step1 = self.tab.steps.create(last_relevant_delta_id=v1, order=0, slug="step-1")
        step2 = self.tab.steps.create(last_relevant_delta_id=v1, order=1, slug="step-2")
        step3 = self.tab.steps.create(last_relevant_delta_id=v1, order=2, slug="step-3")

        cmd = self.run_with_async_db(
            commands.do(
                ReorderSteps,
                workflow_id=self.workflow.id,
                tab=self.tab,
                new_order=[step1.id, step3.id, step2.id],
            )
        )
        v2 = cmd.id
        self.assertStepVersions([v1, v2, v2])
        step2.refresh_from_db()
        step3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)),
            [step1.id, step3.id, step2.id],
        )

        # undo
        self.run_with_async_db(commands.undo(cmd))
        self.assertStepVersions([v1, v1, v1])
        step2.refresh_from_db()
        step3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)),
            [step1.id, step2.id, step3.id],
        )

        # redo
        self.run_with_async_db(commands.redo(cmd))
        self.assertStepVersions([v1, v2, v2])
        step2.refresh_from_db()
        step3.refresh_from_db()
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)),
            [step1.id, step3.id, step2.id],
        )

    def test_reorder_modules_reject_other_tabs(self):
        """
        User cannot game the system: only one tab is allowed.

        (A user should not be able to affect Steps outside of his/her
        workflow. There's nothing in the architecture that could lead us there,
        but let's be absolutely sure by testing.)
        """
        v1 = self.delta.id
        step1 = self.tab.steps.create(last_relevant_delta_id=v1, order=0, slug="step-1")
        step2 = self.tab.steps.create(last_relevant_delta_id=v1, order=1, slug="step-2")

        tab2 = self.workflow.tabs.create(position=1, slug="tab-2")
        step3 = tab2.steps.create(last_relevant_delta_id=v1, order=2, slug="step-3")

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderSteps,
                    workflow_id=self.workflow.id,
                    tab=self.tab,
                    new_order=[step1.id, step3.id, step2.id],
                )
            )

    def test_missing_step_valueerror(self):
        step1 = self.tab.steps.create(
            last_relevant_delta_id=self.delta.id, order=0, slug="step-1"
        )
        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderSteps,
                    workflow_id=self.workflow.id,
                    tab=self.tab,
                    new_order=[step1.id + 1],
                )
            )

    def test_non_array_valueerror(self):
        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderSteps,
                    workflow_id=self.workflow.id,
                    tab=self.tab,
                    new_order={"not": "an array"},
                )
            )

    def test_not_enough_steps_valueerror(self):
        step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderSteps,
                    workflow_id=self.workflow.id,
                    tab=self.tab,
                    new_order=[step1.id],
                )
            )

    def test_repeated_steps_valueerror(self):
        step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    ReorderSteps,
                    workflow_id=self.workflow.id,
                    tab=self.tab,
                    new_order=[step1.id, step1.id],
                )
            )

    def test_no_change_does_nothing(self):
        step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=self.delta.id
        )
        step2 = self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=self.delta.id
        )

        cmd = self.run_with_async_db(
            commands.do(
                ReorderSteps,
                workflow_id=self.workflow.id,
                tab=self.tab,
                new_order=[step1.id, step2.id],
            )
        )
        self.assertIsNone(cmd)
