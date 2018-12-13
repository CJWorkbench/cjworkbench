from unittest.mock import patch
from dateutil.parser import isoparse
from django.contrib.auth.models import User
from server.handlers.workflow import set_name, set_position
from server.models import Workflow
from server.models.commands import ChangeWorkflowTitleCommand
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


class WorkflowTest(HandlerTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_set_name(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user, name='A')

        response = self.run_handler(set_name, user=user, workflow=workflow,
                                    name='B')
        self.assertResponse(response, data=None)

        command = ChangeWorkflowTitleCommand.objects.first()
        self.assertEqual(command.new_value, 'B')
        self.assertEqual(command.old_value, 'A')

        workflow.refresh_from_db()
        self.assertEqual(workflow.name, 'B')

    def test_set_name_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)

        response = self.run_handler(set_name, workflow=workflow, name='B')
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_set_name_coerce_to_str(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user, name='A')

        response = self.run_handler(set_name, user=user, workflow=workflow,
                                    name=['B', {'x': 'y'}])
        self.assertResponse(response, data=None)

        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "['B', {'x': 'y'}]")

    def test_set_position(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab2 = workflow.tabs.create(position=1)
        tab2.wf_modules.create(order=0)
        tab2.wf_modules.create(order=1)
        wf_module = tab2.wf_modules.create(order=2)

        response = self.run_handler(set_position, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response, data=None)

        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)
        tab2.refresh_from_db()
        self.assertEqual(tab2.selected_wf_module_position, 2)

    def test_set_position_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_position, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_set_position_ignore_other_workflow(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)

        workflow2 = Workflow.create_and_init(owner=user)
        wf_module = workflow2.tabs.first().wf_modules.create(order=2)

        response = self.run_handler(set_position, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response, error='Invalid wfModuleId')
