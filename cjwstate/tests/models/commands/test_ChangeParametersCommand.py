import logging
from unittest.mock import patch

from cjwstate import commands
from cjwstate.models import Workflow
from cjwstate.models.commands import ChangeParametersCommand, InitWorkflowCommand
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class ChangeParametersCommandTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_change_parameters(self):
        # Setup: workflow with loadurl module
        #
        # loadurl is a good choice because it has three parameters, two of
        # which are useful.
        workflow = Workflow.create_and_init()

        module_zipfile = create_module_zipfile(
            "loadurl",
            spec_kwargs={
                "parameters": [
                    {"id_name": "url", "type": "string"},
                    {"id_name": "has_header", "type": "checkbox", "name": "HH"},
                    {"id_name": "version_select", "type": "custom"},
                ]
            },
        )

        params1 = {
            "url": "http://example.org",
            "has_header": True,
            "version_select": "",
        }

        step = workflow.tabs.first().steps.create(
            module_id_name="loadurl",
            order=0,
            slug="step-1",
            last_relevant_delta_id=workflow.last_delta_id,
            params=params1,
            cached_migrated_params=params1,
            cached_migrated_params_module_version=module_zipfile.version,
        )

        # Create and apply delta. It should change params.
        self.kernel.migrate_params.side_effect = lambda m, p: p
        with self.assertLogs(level=logging.INFO):
            cmd = self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    step=step,
                    new_values={"url": "http://example.com/foo", "has_header": False},
                )
            )
        step.refresh_from_db()

        params2 = {
            "url": "http://example.com/foo",
            "has_header": False,
            "version_select": "",
        }
        self.assertEqual(step.params, params2)

        # undo
        with self.assertLogs(level=logging.INFO):
            # building clientside.Update will migrate_params(), so we need
            # to capture logs.
            self.run_with_async_db(commands.undo(cmd))
        step.refresh_from_db()
        self.assertEqual(step.params, params1)

        # redo
        with self.assertLogs(level=logging.INFO):
            # building clientside.Update will migrate_params(), so we need
            # to capture logs.
            self.run_with_async_db(commands.redo(cmd))
        step.refresh_from_db()
        self.assertEqual(step.params, params2)

    def test_change_parameters_on_soft_deleted_step(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
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
                step=step,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    def test_change_parameters_on_soft_deleted_tab(self):
        workflow = Workflow.objects.create()
        delta = InitWorkflowCommand.create(workflow)
        tab = workflow.tabs.create(position=0, is_deleted=True)

        step = tab.steps.create(
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
                step=step,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    def test_change_parameters_on_hard_deleted_step(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile("loadurl")

        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="loadurl",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"url": ""},
        )
        step.delete()

        cmd = self.run_with_async_db(
            commands.do(
                ChangeParametersCommand,
                workflow_id=workflow.id,
                step=step,
                new_values={"url": "https://example.com"},
            )
        )
        self.assertIsNone(cmd)

    def test_change_parameters_across_module_versions(self):
        workflow = Workflow.create_and_init()

        # Initialize a Step that used module 'x' version '1' (which we
        # don't need to write in code -- after all, that version might be long
        # gone when ChangeParametersCommand is called.
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"version": "v1", "x": 1},  # version-'1' params
            cached_migrated_params={"version": "v1", "x": 1},
            cached_migrated_params_module_version="v1",
        )

        # Now install version '2' of module 'x'.
        #
        # Version '2''s migrate_params() could do anything; in this test, it
        # simply changes 'version' from 'v1' to 'v2'
        create_module_zipfile(
            "x",
            spec_kwargs={
                "parameters": [
                    {"id_name": "version", "type": "string"},
                    {"id_name": "x", "type": "integer"},
                ]
            },
        )
        self.kernel.migrate_params.side_effect = lambda m, p: {**p, "version": "v2"}

        # Now the user requests to change params.
        #
        # The user was _viewing_ version '2' of module 'x', though
        # `step.params` was at version 1. (Workbench ran
        # `migrate_params()` without saving the result when it
        # presented `params` to the user.) So the changes should apply atop
        # _migrated_ params.
        with self.assertLogs(level=logging.INFO):
            cmd = self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    step=step,
                    new_values={"x": 2},
                )
            )
        self.assertEqual(
            step.params,
            {
                "version": "v2",  # migrate_params() ran
                "x": 2,  # and we applied changes on top of its output
            },
        )

        with self.assertLogs(level=logging.INFO):
            # building clientside.Update will migrate_params(), so we need
            # to capture logs.
            self.run_with_async_db(commands.undo(cmd))
        self.assertEqual(
            step.params, {"version": "v1", "x": 1}  # exactly what we had before
        )

    def test_change_parameters_deny_invalid_params(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"x": 1},
        )

        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "x", "type": "integer"}]}
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p

        with self.assertRaises(ValueError), self.assertLogs(level=logging.INFO):
            # Now the user requests to change params, giving an invalid param.
            self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    step=step,
                    new_values={"x": "Threeve"},
                )
            )

    def test_change_parameters_update_tab_delta_ids(self):
        workflow = Workflow.create_and_init()

        # Build the modules
        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "x", "type": "integer"}]}
        )
        create_module_zipfile(
            "tabby", spec_kwargs={"parameters": [{"id_name": "tab", "type": "tab"}]}
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p

        # tab1's step1 depends on tab2's step2
        step1 = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="tabby",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"tab": "tab-2"},
        )
        tab2 = workflow.tabs.create(position=1, slug="tab-2")
        step2 = tab2.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            params={"x": 1},
        )

        with self.assertLogs(level=logging.INFO):
            cmd = self.run_with_async_db(
                commands.do(
                    ChangeParametersCommand,
                    workflow_id=workflow.id,
                    step=step2,
                    new_values={"x": 2},
                )
            )

        step1.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step1.last_relevant_delta_id, cmd.id)
        self.assertEqual(step2.last_relevant_delta_id, cmd.id)
