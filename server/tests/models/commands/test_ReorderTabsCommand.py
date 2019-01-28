from unittest.mock import patch
from server.models import Workflow
from server.models.commands import ReorderTabsCommand
from server.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


class ReorderTabsCommandTest(DbTestCase):
    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_reorder_slugs(self):
        workflow = Workflow.create_and_init()  # tab slug: tab-1
        workflow.tabs.create(position=1, slug='tab-2')
        workflow.tabs.create(position=2, slug='tab-3')

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=['tab-3', 'tab-1', 'tab-2']
        ))
        self.assertEqual(
            list(workflow.live_tabs.values_list('slug', 'position')),
            [('tab-3', 0), ('tab-1', 1), ('tab-2', 2)]
        )

        self.run_with_async_db(cmd.backward())
        self.assertEqual(
            list(workflow.live_tabs.values_list('slug', 'position')),
            [('tab-1', 0), ('tab-2', 1), ('tab-3', 2)]
        )

        self.run_with_async_db(cmd.forward())
        self.assertEqual(
            list(workflow.live_tabs.values_list('slug', 'position')),
            [('tab-3', 0), ('tab-1', 1), ('tab-2', 2)]
        )

    @patch('server.websockets.ws_client_send_delta_async', async_noop)
    def test_adjust_selected_tab_position(self):
        # tab slug: tab-1
        workflow = Workflow.create_and_init(selected_tab_position=2)
        workflow.tabs.create(position=1, slug='tab-2')
        workflow.tabs.create(position=2, slug='tab-3')

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=['tab-3', 'tab-1', 'tab-2']
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

        # initial tab slug: tab-1
        workflow = Workflow.create_and_init(selected_tab_position=2)
        workflow.tabs.create(position=1, slug='tab-2')
        workflow.tabs.create(position=2, slug='tab-3')

        self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=['tab-3', 'tab-1', 'tab-2']
        ))

        delta = send_delta.call_args[0][1]
        self.assertEqual(delta['updateWorkflow']['tab_slugs'],
                         ['tab-3', 'tab-1', 'tab-2'])

    def test_disallow_duplicate_tab_slug(self):
        workflow = Workflow.create_and_init()  # tab 1 slug: tab-1
        workflow.tabs.create(position=1, slug='tab-2')

        with self.assertRaises(ValueError):
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=['tab-1', 'tab-1', 'tab-2']
            ))

    def test_disallow_missing_tab_slug(self):
        workflow = Workflow.create_and_init()  # initial tab slug: tab-1
        workflow.tabs.create(position=1, slug='tab-2')

        with self.assertRaises(ValueError):
            self.run_with_async_db(ReorderTabsCommand.create(
                workflow=workflow,
                new_order=['tab-1']
            ))

    def test_no_op(self):
        workflow = Workflow.create_and_init()  # initial tab slug: tab-1
        workflow.tabs.create(position=1, slug='tab-2')

        cmd = self.run_with_async_db(ReorderTabsCommand.create(
            workflow=workflow,
            new_order=['tab-1', 'tab-2']
        ))
        self.assertIsNone(cmd)
