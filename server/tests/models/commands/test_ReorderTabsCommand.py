import asyncio
from unittest.mock import patch
from server.models import Workflow
from server.models.commands import ReorderTabsCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class ReorderTabsCommandTest(DbTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_reorder_ids(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)
        tab3 = workflow.tabs.create(position=2)

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=[tab3.id, tab1.id, tab2.id]
        ))
        self.assertEqual(
            list(workflow.live_tabs.values_list('id', 'position')),
            [(tab3.id, 0), (tab1.id, 1), (tab2.id, 2)]
        )

        self.run_with_async_db(cmd.backward())
        self.assertEqual(
            list(workflow.live_tabs.values_list('id', 'position')),
            [(tab1.id, 0), (tab2.id, 1), (tab3.id, 2)]
        )

        self.run_with_async_db(cmd.forward())
        self.assertEqual(
            list(workflow.live_tabs.values_list('id', 'position')),
            [(tab3.id, 0), (tab1.id, 1), (tab2.id, 2)]
        )

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_adjust_selected_tab_position(self):
        workflow = Workflow.create_and_init(selected_tab_position=2)
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)
        tab3 = workflow.tabs.create(position=2)

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=[tab3.id, tab1.id, tab2.id]
        ))
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

        self.run_with_async_db(cmd.backward())
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 2)

        self.run_with_async_db(cmd.forward())
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 0)

    @patch('server.websockets.ws_client_send_delta_async')
    def test_ws_data(self, send_delta):
        send_delta.return_value = async_noop()

        workflow = Workflow.create_and_init(selected_tab_position=2)
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)
        tab3 = workflow.tabs.create(position=2)

        self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=[tab3.id, tab1.id, tab2.id]
        ))

        delta = send_delta.call_args[0][1]
        self.assertEqual(delta['updateWorkflow']['tab_ids'],
                         [tab3.id, tab1.id, tab2.id])

    def test_disallow_duplicate_tab_id(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)

        with self.assertRaises(ValueError):
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=[tab1.id, tab1.id, tab2.id]
            ))

    def test_disallow_missing_tab_id(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        workflow.tabs.create(position=1)

        with self.assertRaises(ValueError):
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=[tab1.id]
            ))

    def test_disallow_unowned_tab_id(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)
        other_workflow = Workflow.create_and_init()
        other_tab = other_workflow.tabs.first()

        with self.assertRaises(ValueError):
            # Does the checker check tab _counts_?
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=[tab1.id, other_tab.id]
            ))

        with self.assertRaises(ValueError):
            # Does the checker check only for _matching_ ids?
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=[tab1.id, tab2.id, other_tab.id]
            ))

    def test_no_op(self):
        workflow = Workflow.create_and_init()
        tab1 = workflow.tabs.first()
        tab2 = workflow.tabs.create(position=1)

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=[tab1.id, tab2.id]
        ))
        self.assertIsNone(cmd)
