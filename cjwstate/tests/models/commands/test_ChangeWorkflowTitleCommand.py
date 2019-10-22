from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import ChangeWorkflowTitleCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class ChangeWorkflowTitleCommandTests(DbTestCase):
    def test_change_title(self):
        workflow = Workflow.create_and_init(name="title1")

        # Change back to second title, see if it saved
        cmd = self.run_with_async_db(
            commands.do(
                ChangeWorkflowTitleCommand, workflow_id=workflow.id, new_value="title2"
            )
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title2")  # test DB change

        # undo
        self.run_with_async_db(commands.undo(cmd))
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title1")  # test DB change

        # redo
        self.run_with_async_db(commands.redo(cmd))
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title2")
