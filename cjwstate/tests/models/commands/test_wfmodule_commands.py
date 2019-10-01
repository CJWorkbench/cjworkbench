import asyncio
from unittest.mock import patch
from cjwstate.models import Delta, ModuleVersion, Workflow, WfModule
from cjwstate.models.commands import (
    AddModuleCommand,
    DeleteModuleCommand,
    InitWorkflowCommand,
)
from cjwstate.modules.loaded_module import LoadedModule
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


class MockLoadedModule:
    def __init__(self, *args):
        pass

    def migrate_params(self, values):
        return values


@patch("server.rabbitmq.queue_render", async_noop)
@patch("cjwstate.models.Delta.ws_notify", async_noop)
class AddDeleteModuleCommandTests(DbTestCase):
    def assertWfModuleVersions(self, expected_versions):
        positions = list(self.tab.live_wf_modules.values_list("order", flat=True))
        self.assertEqual(positions, list(range(0, len(expected_versions))))

        versions = list(
            self.tab.live_wf_modules.values_list("last_relevant_delta_id", flat=True)
        )
        self.assertEqual(versions, expected_versions)

    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        self.module_version = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "loadurl",
                "name": "Load URL",
                "category": "Clean",
                "parameters": [{"id_name": "url", "type": "string"}],
            },
            source_version_hash="1.0",
        )

        self.delta = InitWorkflowCommand.create(self.workflow)

    # Add another module, then undo, redo
    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_module(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        all_modules = self.tab.live_wf_modules

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Add a module, insert before the existing one, check to make sure it
        # went there and old one is after
        cmd = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_version.id_name,
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
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertEqual(cmd.prev_delta_id, self.delta.id)
        with self.assertRaises(Delta.DoesNotExist):
            cmd.next_delta

        # undo! undo! ahhhhh everything is on fire! undo!
        self.run_with_async_db(cmd.backward())
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)

        # wait no, we wanted that module
        self.run_with_async_db(cmd.forward())
        self.assertEqual(all_modules.count(), 2)
        added_module = all_modules.get(order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = all_modules.get(order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling
        # WfModule too
        self.run_with_async_db(cmd.backward())
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)
        cmd.delete_with_successors()
        with self.assertRaises(WfModule.DoesNotExist):
            all_modules.get(pk=added_module.id)  # should be gone

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_module_default_params(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "blah",
                "name": "Blah",
                "category": "Clean",
                "parameters": [
                    {"id_name": "a", "type": "string", "default": "x"},
                    {"id_name": "c", "type": "checkbox", "name": "C", "default": True},
                ],
            },
            source_version_hash="1.0",
        )

        cmd = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=workflow,
                tab=workflow.tabs.first(),
                slug="step-1",
                module_id_name=module_version.id_name,
                position=0,
                param_values={},
            )
        )
        self.assertEqual(cmd.wf_module.params, {"a": "x", "c": True})

    def test_add_module_raise_slug_not_unique(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.wf_modules.create(order=0, slug="step-1", module_id_name="x")
        # module_id_name doesn't exist either, but we'll white-box test and
        # assume the uniqueness check comes first
        with self.assertRaisesRegex(ValueError, "unique"):
            self.run_with_async_db(
                AddModuleCommand.create(
                    workflow=workflow,
                    tab=tab,
                    slug="step-1",
                    module_id_name="x",
                    position=0,
                    param_values={},
                )
            )

    def test_add_module_raise_module_version_does_not_exist(self):
        workflow = Workflow.create_and_init()
        with self.assertRaises(ModuleVersion.DoesNotExist):
            self.run_with_async_db(
                AddModuleCommand.create(
                    workflow=workflow,
                    tab=workflow.tabs.first(),
                    slug="step-1",
                    module_id_name="doesnotexist",
                    position=0,
                    param_values={},
                )
            )

    def test_add_module_validate_params(self):
        workflow = Workflow.create_and_init()
        module_version = ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "blah",
                "name": "Blah",
                "category": "Clean",
                "parameters": [{"id_name": "a", "type": "string"}],
            },
            source_version_hash="1.0",
        )

        with self.assertRaises(ValueError):
            self.run_with_async_db(
                AddModuleCommand.create(
                    workflow=workflow,
                    tab=workflow.tabs.first(),
                    slug="step-1",
                    module_id_name=module_version.id_name,
                    position=0,
                    param_values={"a": 3},
                )
            )

    # Try inserting at various positions to make sure the renumbering works
    # right Then undo multiple times
    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_many_modules(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # beginning state: one WfModule
        all_modules = self.tab.live_wf_modules

        # Insert at beginning
        cmd1 = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )
        v2 = cmd1.id
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.wf_module.order, 0)
        self.assertNotEqual(cmd1.wf_module, existing_module)
        v2 = cmd1.id
        self.assertWfModuleVersions([v2, v2])

        # Insert at end
        cmd2 = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-3",
                module_id_name=self.module_version.id_name,
                position=2,
                param_values={},
            )
        )
        v3 = cmd2.id
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.wf_module.order, 2)
        self.assertWfModuleVersions([v2, v2, v3])

        # Insert in between two modules
        cmd3 = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-4",
                module_id_name=self.module_version.id_name,
                position=2,
                param_values={},
            )
        )
        v4 = cmd3.id
        self.assertEqual(all_modules.count(), 4)
        self.assertEqual(cmd3.wf_module.order, 2)
        self.assertWfModuleVersions([v2, v2, v4, v4])

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
        self.run_with_async_db(cmd3.backward())
        self.assertWfModuleVersions([v2, v2, v3])
        self.run_with_async_db(cmd2.backward())
        self.assertWfModuleVersions([v2, v2])
        self.run_with_async_db(cmd1.backward())
        self.assertWfModuleVersions([v1])
        self.assertEqual(
            list(all_modules.values_list("id", flat=True)), [existing_module.id]
        )

    # Delete module, then undo, redo
    def test_delete_module(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        all_modules = self.tab.live_wf_modules

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id
        self.assertWfModuleVersions([v1])

        # Delete it. Yeah, you better run.
        cmd = self.run_with_async_db(
            DeleteModuleCommand.create(
                workflow=self.workflow, wf_module=existing_module
            )
        )
        self.assertEqual(all_modules.count(), 0)
        self.assertWfModuleVersions([])

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
        self.run_with_async_db(cmd.backward())
        self.assertEqual(all_modules.count(), 1)
        self.assertWfModuleVersions([v1])
        self.assertEqual(all_modules.first(), existing_module)

    # ensure that deleting the selected module sets the selected module to
    # null, and is undoable
    def test_delete_selected(self):
        wf_module = self.tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )
        self.tab.selected_wf_module_position = 0
        self.tab.save(update_fields=["selected_wf_module_position"])

        cmd = self.run_with_async_db(
            DeleteModuleCommand.create(workflow=self.workflow, wf_module=wf_module)
        )

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_wf_module_position)

        self.run_with_async_db(cmd.backward())  # don't crash

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_undo_add_only_selected(self):
        """Undoing the only add sets selection to None."""
        cmd = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )

        self.tab.selected_wf_module_position = 0
        self.tab.save(update_fields=["selected_wf_module_position"])

        self.run_with_async_db(cmd.backward())

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_wf_module_position)

    # ensure that adding a module, selecting it, then undo add, prevents
    # dangling selected_wf_module (basically the AddModule equivalent of
    # test_delete_selected)
    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_undo_selected(self):
        """Undoing an add sets selection."""
        self.tab.wf_modules.create(
            order=0,
            slug="step-1",
            last_relevant_delta_id=self.delta.id,
            params={"url": ""},
        )

        # beginning state: one WfModule
        all_modules = self.tab.live_wf_modules
        self.assertEqual(all_modules.count(), 1)

        cmd = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_version.id_name,
                position=1,
                param_values={},
            )
        )

        self.tab.selected_wf_module_position = 1
        self.tab.save(update_fields=["selected_wf_module_position"])

        self.run_with_async_db(cmd.backward())

        self.tab.refresh_from_db()
        self.assertEqual(self.tab.selected_wf_module_position, 0)

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_to_empty_tab_affects_dependent_tab_wf_modules(self):
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "tabby",
                "name": "Tabby",
                "category": "Clean",
                "parameters": [{"id_name": "tab", "type": "tab"}],
            }
        )

        wfm1 = self.workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="tabby",
            last_relevant_delta_id=self.workflow.last_delta_id,
            params={"tab": "tab-2"},
        )

        tab2 = self.workflow.tabs.create(position=1, slug="tab-2")

        # Now add a module to tab2.
        cmd = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=tab2,
                slug="step-2",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={"url": "https://x.com"},
            )
        )

        # Tab1's "tabby" module depends on tab2, so it should update.
        wfm1.refresh_from_db()
        self.assertEqual(wfm1.last_relevant_delta_id, cmd.id)

    # We had a bug where add then delete caused an error when deleting
    # workflow, since both commands tried to delete the WfModule
    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_add_delete(self):
        cmda = self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )
        self.run_with_async_db(
            DeleteModuleCommand.create(workflow=self.workflow, wf_module=cmda.wf_module)
        )
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_delete_if_workflow_delete_cascaded_to_wf_module_first(self):
        self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )
        # Add a second command -- so we test what happens when deleting
        # multiple deltas while deleting the workflow.
        self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-2",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass

    @patch.object(LoadedModule, "for_module_version", MockLoadedModule)
    def test_delete_if_workflow_missing_init(self):
        self.workflow.last_delta_id = None
        self.workflow.save(update_fields=["last_delta_id"])

        self.delta.delete()
        self.run_with_async_db(
            AddModuleCommand.create(
                workflow=self.workflow,
                tab=self.workflow.tabs.first(),
                slug="step-1",
                module_id_name=self.module_version.id_name,
                position=0,
                param_values={},
            )
        )

        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass
