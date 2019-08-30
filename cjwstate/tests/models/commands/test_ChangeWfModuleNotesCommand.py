from unittest.mock import patch
from cjwstate.models import Workflow
from cjwstate.models.commands import ChangeWfModuleNotesCommand
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch("server.rabbitmq.queue_render", async_noop)
@patch("cjwstate.models.Delta.ws_notify", async_noop)
class ChangeWfModuleNotesCommandTests(DbTestCase):
    def test_change_notes(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            notes="text1",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        # do
        cmd = self.run_with_async_db(
            ChangeWfModuleNotesCommand.create(
                workflow=workflow, wf_module=wf_module, new_value="text2"
            )
        )
        self.assertEqual(wf_module.notes, "text2")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, "text2")

        # undo
        self.run_with_async_db(cmd.backward())
        self.assertEqual(wf_module.notes, "text1")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, "text1")

        # redo
        self.run_with_async_db(cmd.forward())
        self.assertEqual(wf_module.notes, "text2")
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, "text2")
