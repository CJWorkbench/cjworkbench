import asyncio
from unittest.mock import patch
from asgiref.sync import async_to_sync
from django.utils import timezone
import pandas as pd
from server.models import Module, ModuleVersion, Workflow, WfModule
from server.models.commands import AddModuleCommand, DeleteModuleCommand, \
        ChangeDataVersionCommand, ChangeWfModuleNotesCommand, \
        ChangeWfModuleUpdateSettingsCommand, ChangeParametersCommand
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        mock_csv_table, mock_csv_table2


async def async_noop(*args, **kwargs):
    pass

future_none = asyncio.Future()
future_none.set_result(None)


class CommandTestCase(DbTestCase):
    def setUp(self):
        super().setUp()
        self.workflow = create_testdata_workflow()

    def assertWfModuleVersions(self, expected_versions):
        result = list(
            self.workflow.wf_modules.values_list('last_relevant_delta_id',
                                                 flat=True)
        )
        self.assertEqual(result, expected_versions)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class AddDeleteModuleCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        # defined by create_testdata_workflow
        self.module_version = ModuleVersion.objects.first()

    # Add another module, then undo, redo
    def test_add_module(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # Add a module, insert before the existing one, check to make sure it
        # went there and old one is after
        cmd = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                     self.module_version, 0,
                                                     {'csv': 'A,B\n1,2'}
        )
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        # Test that supplied param is written
        self.assertEqual(
            len(added_module.parameter_vals.filter(value='A,B\n1,2')),
            1
        )
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        self.assertGreater(self.workflow.revision(), v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo! undo! ahhhhh everything is on fire! undo!
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)

        # wait no, we wanted that module
        async_to_sync(cmd.forward)()
        self.assertEqual(all_modules.count(), 2)
        added_module = WfModule.objects.get(workflow=self.workflow, order=0)
        self.assertNotEqual(added_module, existing_module)
        bumped_module = WfModule.objects.get(workflow=self.workflow, order=1)
        self.assertEqual(bumped_module, existing_module)

        # Undo and test deleting the un-applied command. Should delete dangling
        # WfModule too
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)
        cmd.delete()
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=added_module.id)  # should be gone

    # Try inserting at various positions to make sure the renumbering works
    # right Then undo multiple times
    def test_add_many_modules(self):
        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # beginning state: one WfModule
        all_modules = self.workflow.wf_modules
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()
        self.assertEqual(existing_module.order, 0)
        self.assertWfModuleVersions([v1])

        # Insert at beginning
        cmd1 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      0, {})
        self.assertEqual(all_modules.count(), 2)
        self.assertEqual(cmd1.wf_module.order, 0)
        self.assertNotEqual(cmd1.wf_module, existing_module)
        v2 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2])

        # Insert at end
        cmd2 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      2, {})
        self.assertEqual(all_modules.count(), 3)
        self.assertEqual(cmd2.wf_module.order, 2)
        v3 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2, v3])

        # Insert in between two modules
        cmd3 = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      2, {})
        self.assertEqual(all_modules.count(), 4)
        self.assertEqual(cmd3.wf_module.order, 2)
        v4 = self.workflow.revision()
        self.assertWfModuleVersions([v2, v2, v4, v4])

        # Check the delta chain, should be 1 <-> 2 <-> 3
        self.workflow.refresh_from_db()
        cmd1.refresh_from_db()
        cmd2.refresh_from_db()
        cmd3.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd3)
        self.assertIsNone(cmd3.next_delta)
        self.assertEqual(cmd3.prev_delta, cmd2)
        self.assertEqual(cmd2.next_delta, cmd3)
        self.assertEqual(cmd2.prev_delta, cmd1)
        self.assertEqual(cmd1.next_delta, cmd2)
        self.assertIsNone(cmd1.prev_delta)

        # We should be able to go all the way back
        async_to_sync(cmd3.backward)()
        self.assertWfModuleVersions([v2, v2, v3])
        async_to_sync(cmd2.backward)()
        self.assertWfModuleVersions([v2, v2])
        async_to_sync(cmd1.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(all_modules.count(), 1)

    # Delete module, then undo, redo
    def test_delete_module(self):
        # beginning state: one WfModule
        all_modules = self.workflow.wf_modules
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()
        self.assertWfModuleVersions([v1])

        # Delete it. Yeah, you better run.
        cmd = async_to_sync(DeleteModuleCommand.create)(existing_module)
        self.assertEqual(all_modules.count(), 0)
        self.assertWfModuleVersions([])

        # workflow revision should have been incremented
        self.workflow.refresh_from_db()
        v2 = self.workflow.revision()
        self.assertGreater(v2, v1)

        # Check the delta chain (short, but should be sweet)
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.last_delta, cmd)
        self.assertIsNone(cmd.prev_delta)
        self.assertIsNone(cmd.next_delta)

        # undo
        async_to_sync(cmd.backward)()
        self.assertEqual(all_modules.count(), 1)
        self.assertWfModuleVersions([v1])
        self.assertEqual(self.workflow.wf_modules.first(), existing_module)

        # nevermind, redo
        async_to_sync(cmd.forward)()
        self.assertEqual(all_modules.count(), 0)

        # Deleting the appplied command should delete dangling WfModule too
        cmd.delete()
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=existing_module.id)  # should be gone

    # ensure that deleting the selected module sets the selected module to
    # null, and is undoable
    def test_delete_selected(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)
        existing_module = WfModule.objects.first()

        self.workflow.selected_wf_module = 0
        self.workflow.save()

        cmd = async_to_sync(DeleteModuleCommand.create)(existing_module)

        self.workflow.refresh_from_db()
        self.assertIsNone(self.workflow.selected_wf_module)

        async_to_sync(cmd.backward)()
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.selected_wf_module, 0)

    # ensure that adding a module, selecting it, then undo add, prevents
    # dangling selected_wf_module (basically the AddModule equivalent of
    # test_delete_selected)
    def test_add_undo_selected(self):
        # beginning state: one WfModule
        all_modules = WfModule.objects.filter(workflow=self.workflow)
        self.assertEqual(all_modules.count(), 1)

        cmd = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                     self.module_version,
                                                     1, {})

        self.workflow.selected_wf_module = cmd.wf_module.order
        self.workflow.save()

        async_to_sync(cmd.backward)()

        self.workflow.refresh_from_db()
        self.assertIsNone(self.workflow.selected_wf_module)

    # We had a bug where add then delete caused an error when deleting
    # workflow, since both commands tried to delete the WfModule
    def test_add_delete(self):
        cmda = async_to_sync(AddModuleCommand.create)(self.workflow,
                                                      self.module_version,
                                                      0, {})
        async_to_sync(DeleteModuleCommand.create)(cmda.wf_module)
        self.workflow.delete()
        self.assertTrue(True)  # we didn't crash! Yay, we pass


@patch('server.models.Delta.ws_notify', async_noop)
class ChangeDataVersionCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.wfm = WfModule.objects.first()

    # Change version, then undo/redo
    @patch('server.models.commands.ChangeDataVersionCommand.schedule_execute',
           async_noop)
    def test_change_data_version(self):
        # Create two data versions, use the second
        firstver = self.wfm.store_fetched_table(mock_csv_table)
        secondver = self.wfm.store_fetched_table(mock_csv_table2)

        self.wfm.set_fetched_data_version(secondver)

        self.workflow.refresh_from_db()
        v1 = self.workflow.revision()

        # Change back to first version
        cmd = async_to_sync(ChangeDataVersionCommand.create)(self.wfm,
                                                             firstver)
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)

        self.workflow.refresh_from_db()
        v2 = self.workflow.revision()
        # workflow revision should have been incremented
        self.assertGreater(v2, v1)
        self.assertWfModuleVersions([v2])

        # undo
        async_to_sync(cmd.backward)()
        self.assertWfModuleVersions([v1])
        self.assertEqual(self.wfm.get_fetched_data_version(), secondver)

        # redo
        async_to_sync(cmd.forward)()
        self.assertWfModuleVersions([v2])
        self.assertEqual(self.wfm.get_fetched_data_version(), firstver)

    @patch('server.rabbitmq.queue_render')
    def test_queue_render_if_notifying(self, queue_render):
        queue_render.return_value = future_none

        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'B': [2]})
        date1 = self.wfm.store_fetched_table(df1)
        date2 = self.wfm.store_fetched_table(df2)

        self.wfm.notifications = True
        self.wfm.set_fetched_data_version(date1)
        self.wfm.save()

        delta = async_to_sync(ChangeDataVersionCommand.create)(self.wfm, date2)

        queue_render.assert_called_with(self.wfm.workflow_id, delta.id)

    @patch('server.websockets.queue_render_if_listening')
    @patch('server.rabbitmq.queue_render')
    def test_queue_render_if_listening_and_no_notification(
        self,
        queue_render,
        queue_render_if_listening
    ):
        queue_render_if_listening.return_value = future_none

        df1 = pd.DataFrame({'A': [1]})
        df2 = pd.DataFrame({'B': [2]})
        date1 = self.wfm.store_fetched_table(df1)
        date2 = self.wfm.store_fetched_table(df2)

        self.wfm.notifications = False
        self.wfm.set_fetched_data_version(date1)
        self.wfm.save()

        delta = async_to_sync(ChangeDataVersionCommand.create)(self.wfm, date2)

        queue_render.assert_not_called()
        queue_render_if_listening.assert_called_with(self.wfm.workflow_id,
                                                     delta.id)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleNotesCommandTests(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.wfm = WfModule.objects.first()

    # Change notes, then undo/redo
    def test_change_notes(self):
        firstNote = 'text1'
        secondNote = 'text2'
        self.wfm.notes = firstNote

        # do
        cmd = async_to_sync(ChangeWfModuleNotesCommand.create)(self.wfm,
                                                               secondNote)
        self.assertEqual(self.wfm.notes, secondNote)

        # undo
        async_to_sync(cmd.backward)()
        self.assertEqual(self.wfm.notes, firstNote)

        # redo
        async_to_sync(cmd.forward)()
        self.assertEqual(self.wfm.notes, secondNote)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeParametersCommandTest(DbTestCase):
    def test_change_parameters(self):
        # Setup: workflow with loadurl module
        #
        # loadurl is a good choice because it has three parameters, two of
        # which are useful.
        workflow = Workflow.objects.create(name='hi')
        module = Module.objects.create(name='loadurl', id_name='loadurl',
                                       dispatch='loadurl')
        module_version = ModuleVersion.objects.create(
            source_version_hash='1.0',
            module=module
        )
        module_version.parameter_specs.create(id_name='url', type='string',
                                              order=0, def_value='')
        module_version.parameter_specs.create(id_name='has_header',
                                              type='checkbox', order=1,
                                              def_value='')
        module_version.parameter_specs.create(id_name='version_select',
                                              type='custom', order=2,
                                              def_value='')
        wf_module = workflow.wf_modules.create(
            order=0,
            module_version=module_version
        )
        # Set original parameters
        wf_module.create_parametervals({
            'url': 'http://example.org',
            'has_header': True,
        })

        params1 = wf_module.get_params().to_painful_dict(pd.DataFrame())

        # Create and apply delta. It should change params.
        cmd = async_to_sync(ChangeParametersCommand.create)(
            workflow=workflow,
            wf_module=wf_module,
            new_values={
                'url': 'http://example.com/foo',
                'has_header': False,
            }
        )
        params2 = wf_module.get_params().to_painful_dict(pd.DataFrame())

        self.assertEqual(params2['url'], 'http://example.com/foo')
        self.assertEqual(params2['has_header'], False)
        self.assertEqual(params2['version_select'], params1['version_select'])

        # undo
        async_to_sync(cmd.backward)()
        params3 = wf_module.get_params().to_painful_dict(pd.DataFrame())
        self.assertEqual(params3, params1)

        # redo
        async_to_sync(cmd.forward)()
        params4 = wf_module.get_params().to_painful_dict(pd.DataFrame())
        self.assertEqual(params4, params2)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ChangeWfModuleUpdateSettingsCommandTests(DbTestCase):
    def test_change_update_settings(self):
        workflow = Workflow.objects.create(name='hi')
        module = Module.objects.create(name='pastecsv', id_name='pastecsv',
                                       dispatch='pastecsv')
        module_version = ModuleVersion.objects.create(
            source_version_hash='1.0',
            module=module
        )
        wf_module = WfModule.objects.create(workflow=workflow, order=0,
                                            module_version=module_version,
                                            auto_update_data=False,
                                            next_update=None,
                                            update_interval=100)

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
        self.assertEqual(wf_module.update_interval, 100)
        wf_module.refresh_from_db()
        self.assertFalse(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, None)
        self.assertEqual(wf_module.update_interval, 100)

        # redo
        async_to_sync(cmd.forward)()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
        wf_module.refresh_from_db()
        self.assertTrue(wf_module.auto_update_data)
        self.assertEqual(wf_module.next_update, mydate)
        self.assertEqual(wf_module.update_interval, 1000)
