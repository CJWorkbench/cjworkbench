from unittest.mock import patch
from dateutil.parser import isoparse
from django.contrib.auth.models import User
from server.handlers.wf_module import set_params, delete, \
        set_stored_data_version, set_notes
from server.models import Workflow
from server.models.commands import ChangeParametersCommand, \
        ChangeWfModuleNotesCommand, DeleteModuleCommand
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


class WfModuleTest(HandlerTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_params(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'bar'})
        self.assertResponse(response, data=None)

        command = ChangeParametersCommand.objects.first()
        self.assertEquals(command.new_values, {'foo': 'bar'})
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

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.websockets.queue_render_if_listening', async_noop)
    def test_set_stored_data_version(self):
        version = '2018-12-12T21:30:00.000Z'
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        wf_module.stored_objects.create(stored_at=isoparse(version), size=0)

        response = self.run_handler(set_stored_data_version, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    version=version)
        self.assertResponse(response, data=None)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.stored_data_version, isoparse(version))

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.websockets.queue_render_if_listening', async_noop)
    def test_set_stored_data_version_command_set_read(self):
        version = '2018-12-12T21:30:00.000Z'
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        so = wf_module.stored_objects.create(stored_at=isoparse(version),
                                             size=0, read=False)

        response = self.run_handler(set_stored_data_version, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    version=version)
        self.assertResponse(response, data=None)
        so.refresh_from_db()
        self.assertEqual(so.read, True)

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.websockets.queue_render_if_listening', async_noop)
    def test_set_stored_data_version_microsecond_date(self):
        version_precise = '2018-12-12T21:30:00.000123Z'
        version_js = '2018-12-12T21:30:00.000Z'
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        # Postgres will store this with microsecond precision
        wf_module.stored_objects.create(stored_at=isoparse(version_precise),
                                        size=0)

        # JS may request it with millisecond precision
        response = self.run_handler(set_stored_data_version, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    version=version_js)
        self.assertResponse(response, data=None)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.stored_data_version,
                         isoparse(version_precise))

    def test_set_stored_data_version_invalid_date(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(set_stored_data_version, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    version=['not a date'])
        self.assertResponse(
            response,
            error='BadRequest: version must be an ISO8601 datetime'
        )

    def test_set_stored_data_version_viewer_access_denied(self):
        version = '2018-12-12T21:30:00.000Z'
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)
        wf_module.stored_objects.create(stored_at=isoparse(version), size=0)

        response = self.run_handler(set_stored_data_version, workflow=workflow,
                                    wfModuleId=wf_module.id, version=version)
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_notes(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0, notes='A')

        response = self.run_handler(set_notes, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id, notes='B')
        self.assertResponse(response, data=None)

        command = ChangeWfModuleNotesCommand.objects.first()
        self.assertEquals(command.new_value, 'B')
        self.assertEquals(command.old_value, 'A')
        self.assertEquals(command.wf_module_id, wf_module.id)
        self.assertEquals(command.workflow_id, workflow.id)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, 'B')

    def test_set_notes_viewer_acces_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0, notes='A')

        response = self.run_handler(set_notes, workflow=workflow,
                                    wfModuleId=wf_module.id, notes='B')
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_notes_forces_str(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0, notes='A')

        response = self.run_handler(set_notes, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id, notes=['a', 'b'])
        self.assertResponse(response, data=None)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, "['a', 'b']")
