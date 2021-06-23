from unittest.mock import patch

from cjwstate import commands, rabbitmq
from cjwstate.models.commands import SetWorkflowTitle
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch.object(rabbitmq, "queue_render", async_noop)
@patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
class SetWorkflowTitleTests(DbTestCase):
    def test_change_title(self):
        workflow = Workflow.create_and_init(name="title1")

        # Change back to second title, see if it saved
        self.run_with_async_db(
            commands.do(SetWorkflowTitle, workflow_id=workflow.id, new_value="title2")
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title2")  # test DB change

        # undo
        self.run_with_async_db(commands.undo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title1")  # test DB change

        # redo
        self.run_with_async_db(commands.redo(workflow.id))
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "title2")
