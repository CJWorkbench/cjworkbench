import asyncio
from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.utils import timezone
import pandas as pd
from server.models import Delta, Module, ModuleVersion, Workflow, WfModule
from server.models.commands import AddModuleCommand, DeleteModuleCommand, \
        ChangeDataVersionCommand, ChangeWfModuleNotesCommand, \
        ChangeWfModuleUpdateSettingsCommand, InitWorkflowCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass

future_none = asyncio.Future()
future_none.set_result(None)


class CommandTestCase(DbTestCase):
    def assertWfModuleVersions(self, expected_versions):
        positions = list(
            self.tab.live_wf_modules.values_list('order', flat=True)
        )
        self.assertEqual(positions, list(range(0, len(expected_versions))))

        versions = list(
            self.tab.live_wf_modules.values_list('last_relevant_delta_id',
                                                 flat=True)
        )
        self.assertEqual(versions, expected_versions)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class AddDeleteModuleCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        module = Module.objects.create(name='a', id_name='a', dispatch='a')
        self.module_version = ModuleVersion.objects.create(
            source_version_hash='1.0',
            module=module
        )
        self.module_version.parameter_specs.create(id_name='url',
                                                   type='string',
                                                   order=0, def_value='')

        self.delta = InitWorkflowCommand.create(self.workflow)

    # Add another module, then undo, redo
    def test_add_module(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )
        existing_module.create_parametervals()

        all_modules = self.tab.live_wf_modules

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Add a module, insert before the existing one, check to make sure it
        # went there and old one is after
        cmd = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={'url': 'https://x.com'}
        )
        self.assertEqual(all_modules.count(), 2)
        added_module = all_modules.get(order=0)
        self.assertNotEqual(added_module, existing_module)
        # Test that supplied param is written
        self.assertEqual(
            added_module.get_params().get_param_string('url'),
            'https://x.com'
        )
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
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)

        # wait no, we wanted that module
        async_to_sync(cmd.forward)()
        self.assertEqual(all_modules.count(), 2)
        added_module = all_modules.get(order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = all_modules.get(order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling
        # WfModule too
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(all_modules.first(), existing_module)
        cmd.delete()
        with self.assertRaises(WfModule.DoesNotExist):
            all_modules.get(pk=added_module.id)  # should be gone

    # Try inserting at various positions to make sure the renumbering works
    # right Then undo multiple times
    def test_add_many_modules(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )
        existing_module.create_parametervals()

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # beginning state: one WfModule
        all_modules = self.tab.live_wf_modules

        # Insert at beginning
        cmd1 = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )
        v2 = cmd1.id
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.wf_module.order, 0)
        self.assertNotEqual(cmd1.wf_module, existing_module)
        v2 = cmd1.id
        self.assertWfModuleVersions([v2, v2])

        # Insert at end
        cmd2 = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=2,
            param_values={}
        )
        v3 = cmd2.id
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.wf_module.order, 2)
        self.assertWfModuleVersions([v2, v2, v3])

        # Insert in between two modules
        cmd3 = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=2,
            param_values={}
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
        async_to_sync(cmd3.backward)()
        self.assertWfModuleVersions([v2, v2, v3])
        async_to_sync(cmd2.backward)()
        self.assertWfModuleVersions([v2, v2])
        async_to_sync(cmd1.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(list(all_modules.values_list('id', flat=True)),
                         [existing_module.id])

    # Delete module, then undo, redo
    def test_delete_module(self):
        existing_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )
        existing_module.create_parametervals()

        all_modules = self.tab.live_wf_modules

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id
        self.assertWfModuleVersions([v1])

        # Delete it. Yeah, you better run.
        cmd = async_to_sync(DeleteModuleCommand.create)(
            workflow=self.workflow,
            wf_module=existing_module
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
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertWfModuleVersions([v1])
        self.assertEqual(all_modules.first(), existing_module)

    # ensure that deleting the selected module sets the selected module to
    # null, and is undoable
    def test_delete_selected(self):
        wf_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )
        wf_module.create_parametervals()
        self.tab.selected_wf_module_position = 0
        self.tab.save(update_fields=['selected_wf_module_position'])

        cmd = async_to_sync(DeleteModuleCommand.create)(workflow=self.workflow,
                                                        wf_module=wf_module)

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_wf_module_position)

        async_to_sync(cmd.backward)()  # don't crash

    def test_undo_add_only_selected(self):
        """Undoing the only add sets selection to None."""
        cmd = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )

        self.tab.selected_wf_module_position = 0
        self.tab.save(update_fields=['selected_wf_module_position'])

        async_to_sync(cmd.backward)()

        self.tab.refresh_from_db()
        self.assertIsNone(self.tab.selected_wf_module_position)

    # ensure that adding a module, selecting it, then undo add, prevents
    # dangling selected_wf_module (basically the AddModule equivalent of
    # test_delete_selected)
    def test_add_undo_selected(self):
        """Undoing an add sets selection."""
        existing_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )
        existing_module.create_parametervals()

        # beginning state: one WfModule
        all_modules = self.tab.live_wf_modules
        self.assertEqual(all_modules.count(), 1)

        cmd = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=1,
            param_values={}
        )

        self.tab.selected_wf_module_position = 1
        self.tab.save(update_fields=['selected_wf_module_position'])

        async_to_sync(cmd.backward)()

        self.tab.refresh_from_db()
        self.assertEqual(self.tab.selected_wf_module_position, 0)

    # We had a bug where add then delete caused an error when deleting
    # workflow, since both commands tried to delete the WfModule
    def test_add_delete(self):
        cmda = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )
        async_to_sync(DeleteModuleCommand.create)(workflow=self.workflow,
                                                  wf_module=cmda.wf_module)
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass

    def test_delete_if_workflow_delete_cascaded_to_wf_module_first(self):
        async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )
        # Add a second command -- so we test what happens when deleting
        # multiple deltas while deleting the workflow.
        async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass

    def test_delete_if_workflow_missing_init(self):
        self.workflow.last_delta_id = None
        self.workflow.save(update_fields=['last_delta_id'])

        self.delta.delete()
        cmd = async_to_sync(AddModuleCommand.create)(
            workflow=self.workflow,
            tab=self.workflow.tabs.first(),
            module_version=self.module_version,
            position=0,
            param_values={}
        )
        
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass


@patch('server.models.Delta.ws_notify', async_noop)
class ChangeDataVersionCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module = self.tab.wf_modules.create(
            order=0,
            last_relevant_delta_id=self.delta.id
        )

    @patch('server.websockets.queue_render_if_listening', async_noop)
    def test_change_data_version(self):
        # Create two data versions, use the second
        date1 = self.wf_module.store_fetched_table(pd.DataFrame({'A': [1]}))
        date2 = self.wf_module.store_fetched_table(pd.DataFrame({'A': [2]}))

        self.wf_module.stored_data_version = date2
        self.wf_module.save()

        self.workflow.refresh_from_db()
        v1 = self.workflow.last_delta_id

        # Change back to first version
        cmd = async_to_sync(ChangeDataVersionCommand.create)(
            workflow=self.workflow,
            wf_module=self.wf_module,
            new_version=date1
        )
        self.assertEqual(self.wf_module.stored_data_version, date1)

        self.workflow.refresh_from_db()
        v2 = cmd.id
        # workflow revision should have been incremented
        self.assertGreater(v2, v1)
        self.assertWfModuleVersions([v2])

        # undo
        async_to_sync(cmd.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(self.wf_module.stored_data_version, date2)

        # redo
        async_to_sync(cmd.forward)()
        self.assertWfModuleVersions([v2])
        self.assertEqual(self.wf_module.stored_data_version, date1)

    @patch('server.rabbitmq.queue_render')
    def test_change_version_queue_render_if_notifying(self, queue_render):
        queue_render.return_value = future_none

        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'B': [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = True
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = async_to_sync(ChangeDataVersionCommand.create)(
            workflow=self.workflow,
            wf_module=self.wf_module,
            new_version=date2
        )

        queue_render.assert_called_with(self.wf_module.workflow_id, delta.id)

    @patch('server.websockets.queue_render_if_listening', async_noop)
    @patch('server.rabbitmq.queue_render', async_noop)
    def test_accept_deleted_version(self):
        """
        Let the user choose whichever version is desired, even if it does not
        exist.

        The errors will be user-visible ... _later_.
        """
        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'B': [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = async_to_sync(ChangeDataVersionCommand.create)(
            workflow=self.workflow,
            wf_module=self.wf_module,
            new_version=date2
        )

        self.wf_module.stored_objects.get(stored_at=date1).delete()

        async_to_sync(delta.backward)()
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date1)

        async_to_sync(delta.forward)()
        self.wf_module.refresh_from_db()
        self.assertEqual(self.wf_module.stored_data_version, date2)

    @patch('server.websockets.queue_render_if_listening')
    @patch('server.rabbitmq.queue_render')
    def test_change_version_queue_render_if_listening_and_no_notification(
        self,
        queue_render,
        queue_render_if_listening
    ):
        queue_render_if_listening.return_value = future_none

        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'B': [2]})
        date1 = self.wf_module.store_fetched_table(df1)
        date2 = self.wf_module.store_fetched_table(df2)

        self.wf_module.notifications = False
        self.wf_module.stored_data_version = date1
        self.wf_module.save()

        delta = async_to_sync(ChangeDataVersionCommand.create)(
            workflow=self.workflow,
            wf_module=self.wf_module,
            new_version=date2
        )

        queue_render.assert_not_called()
        queue_render_if_listening.assert_called_with(self.wf_module.workflow_id,
                                                     delta.id)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleNotesCommandTests(CommandTestCase):
    def test_change_notes(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wf_module = tab.wf_modules.create(
            order=0,
            notes='text1',
            last_relevant_delta_id=delta.id
        )

        # do
        cmd = async_to_sync(ChangeWfModuleNotesCommand.create)(wf_module,
                                                               'text2')
        self.assertEqual(wf_module.notes, 'text2')
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, 'text2')

        # undo
        async_to_sync(cmd.backward)()
        self.assertEqual(wf_module.notes, 'text1')
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, 'text1')

        # redo
        async_to_sync(cmd.forward)()
        self.assertEqual(wf_module.notes, 'text2')
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.notes, 'text2')


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleUpdateSettingsCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create()
        self.delta = InitWorkflowCommand.create(self.workflow)
        self.tab = self.workflow.tabs.create(position=0)
        module = Module.objects.create(name='a', id_name='a', dispatch='a')
        self.module_version = ModuleVersion.objects.create(
            source_version_hash='1.0',
            module=module
        )

    def test_change_update_settings(self):
        wf_module = self.tab.wf_modules.create(
            module_version=self.module_version,
            last_relevant_delta_id=self.delta.id,
            order=0,
            auto_update_data=False,
            next_update=None,
            update_interval=600
        )

        # do
        mydate = timezone.now()
        cmd = async_to_sync(ChangeWfModuleUpdateSettingsCommand.create)(
            wf_module,
            True,
            mydate,
            1000
        )
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
        wf_module.refresh_from_db()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)

        # undo
        async_to_sync(cmd.backward)()
        self.assertFalse(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, None)
        self.assertEqual(wf_module.update_interval, 600)
        wf_module.refresh_from_db()
        self.assertFalse(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, None)
        self.assertEqual(wf_module.update_interval, 600)

        # redo
        async_to_sync(cmd.forward)()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
        wf_module.refresh_from_db()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
