import asyncio
from unittest.mock import patch
from cjwstate import commands
from cjwstate.models import Delta, Workflow, Step
from cjwstate.models.commands import AddStep, DeleteStep, InitWorkflow
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class AddDeleteStepTests(DbTestCaseWithModuleRegistryAndMockKernel):
    def assertStepVersions(self, expected_versions):
        positions = list(self.tab.live_steps.values_list("order", flat=True))
        self.assertEqual(positions, list(range(0, len(expected_versions))))

        versions = list(
            self.tab.live_steps.values_list("last_relevant_delta_id", flat=True)
        )
        self.assertEqual(versions, expected_versions)

    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        self.module_zipfile = create_module_zipfile(
            "loadsomething",
            spec_kwargs={"parameters": [{"id_name": "url", "type": "string"}]},
        )
        self.kernel.migrate_params.side_effect = RuntimeError(
            "AddStep and tests should cache migrated params correctly"
        )

        self.delta = InitWorkflow.create(self.workflow)

    # Add another module, then undo, redo
    def test_add_module(self):
        existing_module = self.tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        all_modules = self.tab.live_steps

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Add a module, insert before the existing one, check to make sure it
        # went there and old one is after
        cmd = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={"url": "https://x.com"},
            )
        )
        self.assertEqual(all_modules.count(), 2)
        added_module = all_modules.get(order=0)
        self.assertNotEqual(added_module, existing_module)
        # Test that supplied param is written
        self.assertEqual(added_module.params["url"], "https://x.com")
        bumped_module = all_modules.get(order=1)
        self.assertEqual(bumped_module, existing_module)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.last_delta_id, v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta_id, cmd.id)
        self.assertEqual(cmd.prev_delta_id, self.delta.id)
        with self.assertRaises(Delta.DoesNotExist):
            cmd.next_delta

        # undo! undo! ahhhhh everything is on fire! undo!
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)

        # wait no, we wanted that module
        self.run_with_async_db(commands.redo(self.workflow.id))
        self.assertEqual(all_modules.count(), 2)
        added_module = all_modules.get(order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = all_modules.get(order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling
        # Step too
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)
        cmd.delete_with_successors()
        with self.assertRaises(Step.DoesNotExist):
            all_modules.get(pk=added_module.id)  # should be gone

    def test_add_module_default_params(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            "blah",
            spec_kwargs={
                "parameters": [
                    {"id_name": "a", "type": "string", "default": "x"},
                    {"id_name": "c", "type": "checkbox", "name": "C", "default": True},
                ]
            },
        )

        cmd = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=workflow.id,
                tab=workflow.tabs.first(),
                slug="step-1",
                module_id_name="blah",
                position=0,
                param_values={},
            )
        )
        self.assertEqual(cmd.step.params, {"a": "x", "c": True})

    def test_add_module_raise_slug_not_unique(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.steps.create(order=0, slug="step-1", module_id_name="x")
        # module_id_name doesn't exist either, but we'll white-box test and
        # assume the uniqueness check comes first
        with self.assertRaisesRegex(ValueError, "unique"):
            self.run_with_async_db(
                commands.do(
                    AddStep,
                    workflow_id=workflow.id,
                    tab=tab,
                    slug="step-1",
                    module_id_name="x",
                    position=0,
                    param_values={},
                )
            )

    def test_add_module_raise_module_key_error(self):
        workflow = Workflow.create_and_init()
        with self.assertRaises(KeyError):
            self.run_with_async_db(
                commands.do(
                    AddStep,
                    workflow_id=workflow.id,
                    tab=workflow.tabs.first(),
                    slug="step-1",
                    module_id_name="doesnotexist",
                    position=0,
                    param_values={},
                )
            )

    def test_add_module_validate_params(self):
        workflow = Workflow.create_and_init()
        create_module_zipfile(
            "blah", spec_kwargs={"parameters": [{"id_name": "a", "type": "string"}]}
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                commands.do(
                    AddStep,
                    workflow_id=workflow.id,
                    tab=workflow.tabs.first(),
                    slug="step-1",
                    module_id_name="blah",
                    position=0,
                    param_values={"a": 3},
                )
            )

    # Try inserting at various positions to make sure the renumbering works
    # right Then undo multiple times
    def test_add_many_modules(self):
        existing_module = self.tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # beginning state: one Step
        all_modules = self.tab.live_steps

        # Insert at beginning
        cmd1 = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={},
            )
        )
        v2 = cmd1.id
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.step.order, 0)
        self.assertNotEqual(cmd1.step, existing_module)
        v2 = cmd1.id
        self.assertStepVersions([v2, v2])

        # Insert at end
        cmd2 = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-3",
                module_id_name=self.module_zipfile.module_id,
                position=2,
                param_values={},
            )
        )
        v3 = cmd2.id
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.step.order, 2)
        self.assertStepVersions([v2, v2, v3])

        # Insert in between two modules
        cmd3 = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-4",
                module_id_name=self.module_zipfile.module_id,
                position=2,
                param_values={},
            )
        )
        v4 = cmd3.id
        self.assertEqual(all_modules.count(), 4)
        self.assertEqual(cmd3.step.order, 2)
        self.assertStepVersions([v2, v2, v4, v4])

        # Check the delta chain, should be 1 <-> 2 <-> 3
        self.workflow.refresh_from_db()
        cmd1.refresh_from_db()
        cmd2.refresh_from_db()
        cmd3.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd3)
        with self.assertRaises(Delta.DoesNotExist):
            cmd3.next_delta
        self.assertEqual(cmd3.prev_delta, cmd2)
        self.assertEqual(cmd2.prev_delta, cmd1)
        self.assertEqual(cmd1.prev_delta_id, self.delta.id)

        # We should be able to go all the way back
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertStepVersions([v2, v2, v3])
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertStepVersions([v2, v2])
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertStepVersions([v1])
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)), [existing_module.id]
        )

    # Delete module, then undo, redo
    def test_delete_module(self):
        existing_module = self.tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        all_modules = self.tab.live_steps

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id
        self.assertStepVersions([v1])

        # Delete it. Yeah, you better run.
        cmd = self.run_with_async_db(
            commands.do(
                DeleteStep,
                workflow_id=self.workflow.id,
                step=existing_module,
            )
        )
        self.assertEqual(all_modules.count(), 0)
        self.assertStepVersions([])

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        v2 = cmd.id
        self.assertGreater(v2, v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertEqual(cmd.prev_delta_id, self.delta.id)
        with self.assertRaises(Delta.DoesNotExist):
            cmd.next_delta

        # undo
        self.run_with_async_db(commands.undo(self.workflow.id))
        self.assertEqual(all_modules.count(), 1)
        self.assertStepVersions([v1])
        self.assertEqual(all_modules.first(), existing_module)

    # ensure that deleting the selected module sets the selected module to
    # null, and is undoable
    def test_delete_selected(self):
        step = self.tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )
        self.tab.selected_step_position = 0
        self.tab.save(update_fields=["selected_step_position"])

        self.run_with_async_db(
            commands.do(DeleteStep, workflow_id=self.workflow.id, step=step)
        )

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_step_position)

        self.run_with_async_db(commands.undo(self.workflow.id))  # don't crash

    def test_undo_add_only_selected(self):
        self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={},
            )
        )

        self.tab.selected_step_position = 0
        self.tab.save(update_fields=["selected_step_position"])

        self.run_with_async_db(commands.undo(self.workflow.id))

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_step_position)

    # ensure that adding a module, selecting it, then undo add, prevents
    # dangling selected_step (basically the AddModule equivalent of
    # test_delete_selected)
    def test_add_undo_selected(self):
        self.tab.steps.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        # beginning state: one Step
        all_modules = self.tab.live_steps
        self.assertEqual(all_modules.count(), 1)

        self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_zipfile.module_id,
                position=1,
                param_values={},
            )
        )

        self.tab.selected_step_position = 1
        self.tab.save(update_fields=["selected_step_position"])

        self.run_with_async_db(commands.undo(self.workflow.id))

        self.tab.refresh_from_db()
        self.assertEqual(self.tab.selected_step_position, 0)

    def test_add_to_empty_tab_affects_dependent_tab_steps(self):
        module_zipfile = create_module_zipfile(
            "tabby", spec_kwargs={"parameters": [{"id_name": "tab", "type": "tab"}]}
        )

        step1 = self.workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            module_id_name="tabby",
            last_relevant_delta_id=self.workflow.last_delta_id,
            params={"tab": "tab-2"},
            cached_migrated_params={"tab": "tab-2"},
            cached_migrated_params_module_version=module_zipfile.version,
        )

        tab2 = self.workflow.tabs.create(position=1, slug="tab-2")

        # Now add a module to tab2.
        cmd = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=tab2,
                slug="step-2",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={"url": "https://x.com"},
            )
        )

        # Tab1's "tabby" module depends on tab2, so it should update.
        step1.refresh_from_db()
        self.assertEqual(step1.last_relevant_delta_id, cmd.id)

    # We had a bug where add then delete caused an error when deleting
    # workflow, since both commands tried to delete the Step
    def test_add_delete(self):
        cmda = self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={},
            )
        )
        self.run_with_async_db(
            commands.do(
                DeleteStep,
                workflow_id=self.workflow.id,
                step=cmda.step,
            )
        )
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass

    def test_delete_if_workflow_delete_cascaded_to_step_first(self):
        self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={},
            )
        )
        # Add a second command -- so we test what happens when deleting
        # multiple deltas while deleting the workflow.
        self.run_with_async_db(
            commands.do(
                AddStep,
                workflow_id=self.workflow.id,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_zipfile.module_id,
                position=0,
                param_values={},
            )
        )
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass
