from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import ModuleVersion, Workflow
from cjwstate.models.commands import InitWorkflowCommand, ChangeParametersCommand
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.modules.param_dtype import ParamDType
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class MockLoadedModule:
    def __init__(self, *args, **kwargs):
        pass

    def migrate_params(self, params):
        return params  # no-op


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class ChangeParametersCommandTest(DbTestCase):
    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_change_parameters(self):
        # Setup: workflow with loadurl module
        #
        # loadurl is a good choice because it has three parameters, two of
        # which are useful.
        workflow = Workflow.create_and_init()

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "loadurl",
                "name": "loadurl",
                "category": "Clean",
                "parameters": [
                    {"id_name": "url", "type": "string"},
                    {"id_name": "has_header", "type": "checkbox", "name": "HH"},
                    {"id_name": "version_select", "type": "custom"},
                ],
            }
        )

        params1 = {
            "url": "http://example.org",
            "has_header": True,
            "version_select": "",
        }

        wf_module = workflow.tabs.first().wf_modules.create(
            module_id_name="loadurl",
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params=params1,
        )

        # Create and apply delta. It should change params.
        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=wf_module,
                new_values={"url": "http://example.com/foo", "has_header": False},
            )
        )
        wf_module.refresh_from_db()

        params2 = {
            "url": "http://example.com/foo",
            "has_header": False,
            "version_select": "",
        }
        self.assertEqual(wf_module.params, params2)

        # undo
        self.run_with_async_db(commands.undo(cmd))
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.params, params1)

        # redo
        self.run_with_async_db(commands.redo(cmd))
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.params, params2)

    def test_change_parameters_on_soft_deleted_wf_module(self):
        workflow = Workflow.create_and_init()

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "loadurl",
                "name": "loadurl",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            }
        )

        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            last_relevant_delta_id=workflow.last_delta_id,
            is_deleted=True,
            params={"url": ""},
        )

        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=wf_module,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    def test_change_parameters_on_soft_deleted_tab(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0, is_deleted=True)

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "loadurl",
                "name": "loadurl",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            }
        )

        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            last_relevant_delta_id=delta.id,
            params={"url": ""},
        )

        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=wf_module,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    def test_change_parameters_on_hard_deleted_wf_module(self):
        workflow = Workflow.create_and_init()

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "loadurl",
                "name": "loadurl",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            }
        )

        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )
        wf_module.delete()

        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=wf_module,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    @patch.object(LoadedModule, "for_module_version")
    def test_change_parameters_across_module_versions(self, load_module):
        workflow = Workflow.create_and_init()

        # Initialize a WfModule that used module 'x' version '1' (which we
        # don't need to write in code -- after all, that version might be long
        # gone when ChangeParametersCommand is called.
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"version": "v1", "x": 1},  # version-'1' params
        )

        # Now install version '2' of module 'x'.
        #
        # Version '2''s migrate_params() could do anything; in this test, it
        # simply changes 'version' from 'v1' to 'v2'
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "x",
                "name": "x",
                "category": "Clean",
                "parameters": [
                    {"id_name": "version", "type": "string"},
                    {"id_name": "x", "type": "integer"},
                ],
            },
            source_version_hash="2",
        )
        load_module.return_value.param_dtype = ParamDType.Dict(
            {"version": ParamDType.String(), "x": ParamDType.Integer()}
        )
        load_module.return_value.migrate_params = lambda params: {
            **params,
            "version": "v2",
        }

        # Now the user requests to change params.
        #
        # The user was _viewing_ version '2' of module 'x', though
        # `wf_module.params` was at version 1. (Workbench ran
        # `migrate_params()` without saving the result when it
        # presented `params` to the user.) So the changes should apply atop
        # _migrated_ params.
        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=wf_module,
                new_values={"x": 2},
            )
        )
        self.assertEqual(
            wf_module.params,
            {
                "version": "v2",  # migrate_params() ran
                "x": 2,  # and we applied changes on top of its output
            },
        )

        self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(
            wf_module.params, {"version": "v1", "x": 1}  # exactly what we had before
        )

    @patch.object(LoadedModule, "for_module_version")
    def test_change_parameters_deny_invalid_params(self, load_module):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"x": 1},
        )

        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "x",
                "name": "x",
                "category": "Clean",
                "parameters": [{"id_name": "x", "type": "integer"}],
            }
        )
        load_module.return_value.param_schema = ParamDType.Dict(
            {"x": ParamDType.Integer()}
        )
        load_module.return_value.migrate_params = lambda x: x

        with self.assertRaises(ValueError):
            # Now the user requests to change params, giving an invalid param.
            self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    wf_module=wf_module,
                    new_values={"x": "Threeve"},
                )
            )

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_change_parameters_update_tab_delta_ids(self):
        workflow = Workflow.create_and_init()
        # tab1's step1 depends on tab2's step2
        step1 = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="tabby",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"tab": "tab-2"},
        )
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        step2 = tab2.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"x": 1},
        )

        # Build the modules
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "x",
                "name": "x",
                "category": "Clean",
                "parameters": [{"id_name": "x", "type": "integer"}],
            }
        )
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "tabby",
                "name": "tabby",
                "category": "Clean",
                "parameters": [{"id_name": "tab", "type": "tab"}],
            }
        )

        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                wf_module=step2,
                new_values={"x": 2},
            )
        )

        step1.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step1.last_relevant_delta_id, cmd.id)
        self.assertEqual(step2.last_relevant_delta_id, cmd.id)
