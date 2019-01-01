from unittest.mock import patch
import pandas as pd
from server.models import ModuleVersion, Workflow
from server.models.commands import InitWorkflowCommand, ChangeParametersCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeParametersCommandTest(DbTestCase):
    def test_change_parameters(self):
        # Setup: workflow with loadurl module
        #
        # loadurl is a good choice because it has three parameters, two of
        # which are useful.
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0)

        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'loadurl',
            'name': 'loadurl',
            'category': 'Test',
            'parameters': [
                {'id_name': 'url', 'type': 'string'},
                {'id_name': 'has_header', 'type': 'checkbox'},
                {'id_name': 'version_select', 'type': 'custom'},
            ]
        })
        wf_module = tab.wf_modules.create(
            module_version=module_version,
            order=0,
            last_relevant_delta_id=delta.id,
            params={
                'url': 'http://example.org',
                'has_header': True,
                'version_select': None
            }
        )

        params1 = wf_module.get_params().as_dict()

        # Create and apply delta. It should change params.
        cmd = self.run_with_async_db(ChangeParametersCommand.create(
            workflow=workflow,
            wf_module=wf_module,
            new_values={
                'url': 'http://example.com/foo',
                'has_header': False,
            }
        ))
        wf_module.refresh_from_db()
        params2 = wf_module.get_params().as_dict()

        self.assertEqual(params2['url'], 'http://example.com/foo')
        self.assertEqual(params2['has_header'], False)
        self.assertEqual(params2['version_select'], params1['version_select'])

        # undo
        self.run_with_async_db(cmd.backward())
        wf_module.refresh_from_db()
        params3 = wf_module.get_params().to_painful_dict(pd.DataFrame())
        self.assertEqual(params3, params1)

        # redo
        self.run_with_async_db(cmd.forward())
        wf_module.refresh_from_db()
        params4 = wf_module.get_params().to_painful_dict(pd.DataFrame())
        self.assertEqual(params4, params2)

    def test_change_parameters_on_soft_deleted_wf_module(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0)

        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'loadurl',
            'name': 'loadurl',
            'category': 'Test',
            'parameters': [
                {'id_name': 'url', 'type': 'string'},
            ]
        })

        wf_module = tab.wf_modules.create(
            order=0,
            module_version=module_version,
            last_relevant_delta_id=delta.id,
            is_deleted=True,
            params={'url': ''}
        )

        cmd = self.run_with_async_db(ChangeParametersCommand.create(
            workflow=workflow,
            wf_module=wf_module,
            new_values={'url': 'https://example.com'}
        ))
        self.assertIsNone(cmd)

    def test_change_parameters_on_soft_deleted_tab(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0, is_deleted=True)

        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'loadurl',
            'name': 'loadurl',
            'category': 'Test',
            'parameters': [
                {'id_name': 'url', 'type': 'string'},
            ]
        })

        wf_module = tab.wf_modules.create(
            order=0,
            module_version=module_version,
            last_relevant_delta_id=delta.id,
            params={'url': ''}
        )

        cmd = self.run_with_async_db(ChangeParametersCommand.create(
            workflow=workflow,
            wf_module=wf_module,
            new_values={'url': 'https://example.com'}
        ))
        self.assertIsNone(cmd)

    def test_change_parameters_on_hard_deleted_wf_module(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0)

        module_version = ModuleVersion.create_or_replace_from_spec({
            'id_name': 'loadurl',
            'name': 'loadurl',
            'category': 'Test',
            'parameters': [
                {'id_name': 'url', 'type': 'string'},
            ]
        })

        wf_module = tab.wf_modules.create(
            order=0,
            module_version=module_version,
            last_relevant_delta_id=delta.id,
            params={'url': ''}
        )
        wf_module.delete()

        cmd = self.run_with_async_db(ChangeParametersCommand.create(
            workflow=workflow,
            wf_module=wf_module,
            new_values={'url': 'https://example.com'}
        ))
        self.assertIsNone(cmd)
