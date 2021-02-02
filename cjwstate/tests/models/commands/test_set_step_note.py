from unittest.mock import patch
from cjwstate import commands, rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.commands import SetStepNote
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch.object(rabbitmq, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class SetStepNoteTests(DbTestCase):
    def test_change_notes(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            notes="text1",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        # do
        self.run_with_async_db(
            commands.do(
                SetStepNote,
                workflow_id=workflow.id,
                step=step,
                new_value="text2",
            )
        )
        self.assertEqual(step.notes, "text2")
        step.refresh_from_db()
        self.assertEqual(step.notes, "text2")

        # undo
        self.run_with_async_db(commands.undo(workflow.id))
        step.refresh_from_db()
        self.assertEqual(step.notes, "text1")

        # redo
        self.run_with_async_db(commands.redo(workflow.id))
        step.refresh_from_db()
        self.assertEqual(step.notes, "text2")
