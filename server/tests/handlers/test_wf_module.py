from unittest.mock import patch
from django.contrib.auth.models import User
from server.handlers.wf_module import set_params, delete
from server.models import Workflow
from server.models.commands import ChangeParametersCommand, DeleteModuleCommand
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


class WfModuleTest(HandlerTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_params(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo':'bar'})
        self.assertResponse(response, data=None)

        command = ChangeParametersCommand.objects.first()
        self.assertEquals(command.new_values, {'foo':'bar'})
        self.assertEquals(command.old_values, {})
        self.assertEquals(command.wf_module_id, wf_module.id)
        self.assertEquals(command.workflow_id, workflow.id)

    def test_set_params_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_params, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'bar'})
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_set_params_invalid_values(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values='foobar')  # String is not Dict
        self.assertResponse(response,
                            error="BadRequest: values must be an Object")

    def test_set_params_invalid_wf_module(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        wf_module = other_workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'bar'})
        self.assertResponse(response, error='DoesNotExist: WfModule not found')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_delete(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(delete, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response, data=None)

        command = DeleteModuleCommand.objects.first()
        self.assertEquals(command.wf_module_id, wf_module.id)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.is_deleted, True)

    def test_delete_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(delete, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_delete_invalid_wf_module(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        wf_module = other_workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(delete, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response, error='DoesNotExist: WfModule not found')
