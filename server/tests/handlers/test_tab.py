from unittest.mock import patch
from django.contrib.auth.models import User
from server.handlers.tab import add_module, reorder_modules
from server.models import Module, Workflow
from server.models.commands import AddModuleCommand, ReorderModulesCommand
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


def noop(*args, **kwargs):
    pass


class TabTest(HandlerTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    @patch('server.utils.log_user_event_from_scope', noop)
    def test_add_module(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        module = Module.objects.create(id_name='amodule')
        module_version = module.module_versions.create()
        module_version.parameter_specs.create(id_name='foo')

        response = self.run_handler(add_module, user=user, workflow=workflow,
                                    tabId=tab.id, position=3,
                                    moduleId=module.id,
                                    paramValues={'foo':'bar'})
        self.assertResponse(response, data=None)

        command = AddModuleCommand.objects.first()
        self.assertEquals(command.order, 3)
        self.assertEquals(
            command.wf_module.get_params().get_param_string('foo'),
            'bar'
        )
        self.assertEquals(command.wf_module.tab_id, tab.id)
        self.assertEquals(command.workflow_id, workflow.id)

    def test_add_module_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        tab = workflow.tabs.first()
        response = self.run_handler(add_module, workflow=workflow,
                                    tabId=tab.id, position=3,
                                    moduleId=1, paramValues={'foo':'bar'})

        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_add_module_invalid_param_values(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        module = Module.objects.create(id_name='amodule')
        module_version = module.module_versions.create()
        module_version.parameter_specs.create(id_name='foo')

        response = self.run_handler(add_module, user=user, workflow=workflow,
                                    tabId=tab.id, position=3,
                                    moduleId=module.id,
                                    paramValues='foobar')
        self.assertResponse(response,
                            error='BadRequest: paramValues must be an Object')

    def test_add_module_invalid_position(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        module = Module.objects.create(id_name='amodule')
        module_version = module.module_versions.create()
        module_version.parameter_specs.create(id_name='foo')

        response = self.run_handler(add_module, user=user, workflow=workflow,
                                    tabId=tab.id, position='foo',
                                    moduleId=module.id,
                                    paramValues={'foo': 'bar'})
        self.assertResponse(response,
                            error='BadRequest: position must be a Number')

    def test_add_module_missing_tab(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        tab = other_workflow.tabs.first()
        module = Module.objects.create(id_name='amodule')
        module_version = module.module_versions.create()
        module_version.parameter_specs.create(id_name='foo')

        response = self.run_handler(add_module, user=user, workflow=workflow,
                                    tabId=tab.id, position=3,
                                    moduleId=module.id,
                                    paramValues={'foo': 'bar'})
        self.assertResponse(response,
                            error='DoesNotExist: Tab not found')

    def test_add_module_missing_module_version(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()

        response = self.run_handler(add_module, user=user, workflow=workflow,
                                    tabId=tab.id, position='foo',
                                    moduleId=123, paramValues={'foo': 'bar'})
        self.assertResponse(response,
                            error='DoesNotExist: ModuleVersion not found')

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_reorder_modules(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        wfm1 = tab.wf_modules.create(order=0)
        wfm2 = tab.wf_modules.create(order=1)

        response = self.run_handler(reorder_modules, user=user,
                                    workflow=workflow, tabId=tab.id,
                                    wfModuleIds=[wfm2.id, wfm1.id])
        self.assertResponse(response, data=None)

        command = ReorderModulesCommand.objects.first()
        self.assertEquals(command.tab_id, tab.id)
        self.assertEquals(command.workflow_id, workflow.id)

    def test_reorder_modules_viewer_denied_access(self):
        workflow = Workflow.create_and_init(public=True)
        tab = workflow.tabs.first()
        wfm1 = tab.wf_modules.create(order=0)
        wfm2 = tab.wf_modules.create(order=1)

        response = self.run_handler(reorder_modules,
                                    workflow=workflow, tabId=tab.id,
                                    wfModuleIds=[wfm2.id, wfm1.id])
        self.assertResponse(response,
                            error='AuthError: no write access to workflow')

    def test_reorder_modules_invalid_wf_module_ids(self):
        user = User.objects.create(username='a', email='a@example.org')
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        wfm1 = tab.wf_modules.create(order=0)
        wfm2 = tab.wf_modules.create(order=1)

        response = self.run_handler(reorder_modules, user=user,
                                    workflow=workflow, tabId=tab.id,
                                    wfModuleIds=[wfm2.id, wfm1.id, 2])
        self.assertResponse(
            response,
            error='new_order does not have the expected elements'
        )
