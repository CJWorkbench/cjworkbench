from unittest.mock import patch
from server.models import LoadedModule, ModuleVersion, Workflow
from server.models.commands import SetTabNameCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    return


class MockLoadedModule:
    def __init__(self, *args, **kwargs):
        pass

    def migrate_params(self, params):
        return params  # no-op


class SetTabNameCommandTest(DbTestCase):
    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    @patch("server.rabbitmq.queue_render", async_noop)
    def test_set_name(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = "foo"
        tab.save(update_fields=["name"])

        cmd = self.run_with_async_db(
            SetTabNameCommand.create(workflow=workflow, tab=tab, new_name="bar")
        )
        tab.refresh_from_db()
        self.assertEqual(tab.name, "bar")

        self.run_with_async_db(cmd.backward())
        tab.refresh_from_db()
        self.assertEqual(tab.name, "foo")

        self.run_with_async_db(cmd.forward())
        tab.refresh_from_db()
        self.assertEqual(tab.name, "bar")

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    @patch("server.rabbitmq.queue_render", async_noop)
    @patch.object(LoadedModule, "for_module_version_sync", MockLoadedModule)
    def test_change_last_relevant_delta_ids_of_dependent_wf_modules(self):
        workflow = Workflow.create_and_init()
        delta_id = workflow.last_delta_id
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1, slug="tab-2", name="Tab 2")

        # Add a WfModule that depends on tab1
        ModuleVersion.create_or_replace_from_spec(
            {
                "id_name": "x",
                "name": "x",
                "category": "Clean",
                "parameters": [{"id_name": "tab", "type": "tab"}],
            }
        )
        wf_module = tab2.wf_modules.create(
            order=0,
            module_id_name="x",
            params={"tab": tab1.slug},
            last_relevant_delta_id=delta_id,
        )

        cmd = self.run_with_async_db(
            SetTabNameCommand.create(
                workflow=workflow, tab=tab1, new_name=tab1.name + "X"
            )
        )
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.last_relevant_delta_id, cmd.id)

    @patch("server.websockets.ws_client_send_delta_async", async_noop)
    @patch("server.rabbitmq.queue_render", async_noop)
    @patch.object(LoadedModule, "for_module_version_sync", MockLoadedModule)
    def test_change_last_relevant_delta_ids_of_self_wf_modules(self):
        """
        Module render() accepts a `tab_name` argument: test it sees a new one.
        """
        workflow = Workflow.create_and_init()
        delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()

        # Add a WfModule that relies on `tab.name` through its 'render' method.
        ModuleVersion.create_or_replace_from_spec(
            {"id_name": "x", "name": "x", "category": "Clean", "parameters": []}
        )
        wf_module = tab.wf_modules.create(
            order=0, module_id_name="x", last_relevant_delta_id=delta_id
        )

        cmd = self.run_with_async_db(
            SetTabNameCommand.create(
                workflow=workflow, tab=tab, new_name=tab.name + "X"
            )
        )
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.last_relevant_delta_id, cmd.id)

    @patch("server.websockets.ws_client_send_delta_async")
    @patch("server.rabbitmq.queue_render", async_noop)
    def test_ws_data(self, send_delta):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = "foo"
        tab.save(update_fields=["name"])

        send_delta.return_value = async_noop()
        cmd = self.run_with_async_db(
            SetTabNameCommand.create(workflow=workflow, tab=tab, new_name="bar")
        )
        send_delta.assert_called()
        delta1 = send_delta.call_args[0][1]
        self.assertEqual(delta1["updateTabs"], {tab.slug: {"name": "bar"}})

        send_delta.return_value = async_noop()
        self.run_with_async_db(cmd.backward())
        delta2 = send_delta.call_args[0][1]
        self.assertEqual(delta2["updateTabs"], {tab.slug: {"name": "foo"}})

    def test_no_op(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        tab.name = "foo"
        tab.save(update_fields=["name"])

        cmd = self.run_with_async_db(
            SetTabNameCommand.create(workflow=workflow, tab=tab, new_name="foo")
        )
        self.assertIsNone(cmd)
