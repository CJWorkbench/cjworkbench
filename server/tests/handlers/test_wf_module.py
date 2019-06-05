import asyncio
from unittest.mock import patch, Mock
from dateutil.parser import isoparse
from django.contrib.auth.models import User
from django.test import override_settings
from server import oauth
from server.handlers.wf_module import set_params, delete, \
        set_stored_data_version, set_notes, set_collapsed, fetch, \
        generate_secret_access_token, delete_secret
from server.models import ModuleVersion, Workflow
from server.models.commands import ChangeParametersCommand, \
        ChangeWfModuleNotesCommand, DeleteModuleCommand
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


class MockLoadedModule:
    def __init__(self, *args):
        pass

    def migrate_params(self, values):
        return values


class WfModuleTest(HandlerTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_set_params(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x'
        )

        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string'},
            ],
        })

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'bar'})
        self.assertResponse(response, data=None)

        command = ChangeParametersCommand.objects.first()
        self.assertEquals(command.new_values, {'foo': 'bar'})
        self.assertEquals(command.old_values, {})
        self.assertEquals(command.wf_module_id, wf_module.id)
        self.assertEquals(command.workflow_id, workflow.id)

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_set_params_invalid_params(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x'
        )

        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string'},
            ],
        })

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo1': 'bar'})
        self.assertResponse(response, error=(
            "ValueError: Value {'foo1': 'bar'} has wrong names: "
            "expected names {'foo'}"
        ))

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_set_params_null_byte_in_json(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x'
        )

        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'x', 'name': 'x', 'category': 'Clean',
            'parameters': [
                {'id_name': 'foo', 'type': 'string'},
            ],
        })

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'b\x00\x00r'})
        self.assertResponse(response, data=None)
        command = ChangeParametersCommand.objects.first()
        self.assertEquals(command.new_values, {'foo': 'br'})

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_params_no_module(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            module_id_name='x'
        )

        response = self.run_handler(set_params, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    values={'foo': 'bar'})
        self.assertResponse(response,
                            error='ValueError: Module x does not exist')

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

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_collapsed(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0,
                                                            is_collapsed=False)

        response = self.run_handler(set_collapsed, user=user,
                                    workflow=workflow,
                                    wfModuleId=wf_module.id, isCollapsed=True)
        self.assertResponse(response, data=None)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.is_collapsed, True)

    def test_set_collapsed_viewer_acces_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0,
                                                            is_collapsed=False)

        response = self.run_handler(set_collapsed, workflow=workflow,
                                    wfModuleId=wf_module.id, isCollapsed=True)
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_set_collapsed_forces_bool(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0,
                                                            is_collapsed=False)

        # bool('False') is true
        response = self.run_handler(set_collapsed, user=user,
                                    workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    isCollapsed='False')
        self.assertResponse(response, data=None)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.is_collapsed, True)

    @patch('server.websockets.ws_client_send_delta_async')
    @patch('server.rabbitmq.queue_fetch')
    def test_fetch(self, queue_fetch, send_delta):
        future_none = asyncio.Future()
        future_none.set_result(None)

        queue_fetch.return_value = future_none
        send_delta.return_value = future_none

        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(fetch, user=user, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response, data=None)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.is_busy, True)
        queue_fetch.assert_called_with(wf_module)
        send_delta.assert_called_with(workflow.id, {
            'updateWfModules': {
                str(wf_module.id): {'is_busy': True, 'fetch_error': ''},
            }
        })

    def test_fetch_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        wf_module = workflow.tabs.first().wf_modules.create(order=0)

        response = self.run_handler(fetch, workflow=workflow,
                                    wfModuleId=wf_module.id)
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_generate_secret_access_token_writer_access_denied(self):
        user = User.objects.create(email='write@example.org')
        workflow = Workflow.create_and_init(public=True)
        workflow.acl.create(email=user.email, can_edit=True)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response,
                            error='AuthError: no owner access to workflow')

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_generate_secret_access_token_no_value_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': None}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response, data={'token': None})

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_generate_secret_access_token_wrong_param_type_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            params={'s': '{"name":"a","secret":"hello"}'}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id, param='a')
        self.assertResponse(response, data={'token': None})

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    def test_generate_secret_access_token_wrong_param_name_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='twitter_credentials')
        self.assertResponse(response, data={'token': None})

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    @patch('server.oauth.OAuthService.lookup_or_none', lambda _: None)
    @override_settings(PARAMETER_OAUTH_SERVICES={'twitter_credentials': {}})
    def test_generate_secret_access_token_no_service_gives_error(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response, error=(
            'AuthError: we only support twitter_credentials'
        ))

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    @patch('server.oauth.OAuthService.lookup_or_none')
    def test_generate_secret_access_token_auth_error_gives_error(self,
                                                                 factory):
        service = Mock(oauth.OAuth2)
        service.generate_access_token_or_str_error.return_value = 'an error'
        factory.return_value = service

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response, error='AuthError: an error')

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    @patch('server.oauth.OAuthService.lookup_or_none')
    def test_generate_secret_access_token_happy_path(self, factory):
        service = Mock(oauth.OAuth2)
        service.generate_access_token_or_str_error.return_value = {
            'access_token': 'a-token',
            'refresh_token': 'something we must never share',
        }
        factory.return_value = service

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(generate_secret_access_token,
                                    user=user, workflow=workflow,
                                    wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response, data={'token': 'a-token'})

    def test_delete_secret_writer_access_denied(self):
        user = User.objects.create(email='write@example.org')
        workflow = Workflow.create_and_init(public=True)
        workflow.acl.create(email=user.email, can_edit=True)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(delete_secret, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response,
                            error='AuthError: no owner access to workflow')

    def test_delete_secret_ignore_non_secret(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'string'},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            params={'foo': 'bar'},
            secrets={}
        )

        response = self.run_handler(delete_secret, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    param='foo')
        self.assertResponse(response, data=None)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.params, {'foo': 'bar'})

    @patch('server.models.loaded_module.LoadedModule.for_module_version_sync',
           MockLoadedModule)
    @patch('server.websockets.ws_client_send_delta_async')
    def test_delete_secret_happy_path(self, send_delta):
        send_delta.return_value = async_noop()

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        ModuleVersion.create_or_replace_from_spec({
            'id_name': 'g',
            'name': 'g',
            'category': 'Clean',
            'parameters': [
                {'id_name': 'google_credentials', 'type': 'secret',
                 'secret_logic': {'provider': 'oauth', 'service': 'google'}},
            ],
        })
        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name='g',
            order=0,
            secrets={'google_credentials': {'name': 'a', 'secret': 'hello'}}
        )

        response = self.run_handler(delete_secret, user=user,
                                    workflow=workflow, wfModuleId=wf_module.id,
                                    param='google_credentials')
        self.assertResponse(response, data=None)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.secrets, {})

        send_delta.assert_called()
        delta = send_delta.call_args[0][1]
        wf_module_delta = delta['updateWfModules'][str(wf_module.id)]
        self.assertEqual(wf_module_delta['secrets'], {})
