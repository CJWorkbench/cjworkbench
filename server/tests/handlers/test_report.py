from unittest.mock import patch
from django.contrib.auth.models import User
from server.handlers.report import (
    add_block,
    delete_block,
    reorder_blocks,
    set_block_markdown,
)
from cjwstate import rabbitmq
from cjwstate.models import Workflow
from .util import HandlerTestCase
from cjwstate.tests.utils import DbTestCase


async def async_noop(*args, **kwargs):
    pass


def noop(*args, **kwargs):
    pass


class ReportTest(HandlerTestCase, DbTestCase):
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_add_block(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user, has_custom_report=True
        )  # with tab-1

        response = self.run_handler(
            add_block,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            position=0,
            slug="block-1",
            type="table",
            tabSlug="tab-1",
        )
        self.assertResponse(response, data=None)

        self.assertEquals(
            list(
                workflow.blocks.values_list("position", "slug", "block_type", "tab_id")
            ),
            [(0, "block-1", "Table", workflow.tabs.first().id)],
        )

        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(update.mutation_id, "mutation-1")

    def test_add_block_viewer_access_denied(self):
        workflow = Workflow.create_and_init(
            public=True, has_custom_report=True
        )  # tab-1
        response = self.run_handler(
            add_block,
            mutationId="mutation-1",
            workflow=workflow,
            position=0,
            slug="block-1",
            type="table",
            tabSlug="tab-1",
        )

        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_add_block_value_error(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user, has_custom_report=True
        )  # with tab-1

        response = self.run_handler(
            add_block,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            position=0,
            slug="block-1",
            type="table",
            tabSlug="tab-that-does-not-exist",
        )
        self.assertResponse(response, error="ValueError: Invalid Table params")

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_delete_block(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user, has_custom_report=True
        )  # with tab-1
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="hi"
        )

        response = self.run_handler(
            delete_block,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-1",
        )
        self.assertResponse(response, data=None)
        self.assertEquals(workflow.blocks.exists(), False)

        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(update.mutation_id, "mutation-1")

    def test_delete_block_does_not_exist(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user, has_custom_report=True
        )  # with tab-1

        response = self.run_handler(
            delete_block,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-does-not-exist",
        )
        self.assertResponse(
            response, error="DoesNotExist: Block matching query does not exist."
        )

    def test_delete_block_viewer_access_denied(self):
        workflow = Workflow.create_and_init(
            public=True, has_custom_report=True
        )  # tab-1
        response = self.run_handler(
            delete_block,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-1",
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_reorder_blocks(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, has_custom_report=True)  # tab-1
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )
        workflow.blocks.create(
            position=1, slug="block-2", block_type="Text", text_markdown="bar"
        )

        response = self.run_handler(
            reorder_blocks,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slugs=["block-2", "block-1"],
        )
        self.assertResponse(response, data=None)

        self.assertEquals(
            list(workflow.blocks.values_list("slug", flat=True)), ["block-2", "block-1"]
        )

        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(update.mutation_id, "mutation-1")

    def test_reorder_blocks_viewer_denied_access(self):
        workflow = Workflow.create_and_init(public=True, has_custom_report=True)
        response = self.run_handler(
            reorder_blocks,
            mutationId="mutation-1",
            workflow=workflow,
            slugs=["don't", "care"],
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_reorder_blocks_invalid_block_slugs(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, has_custom_report=True)  # tab-1
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        response = self.run_handler(
            reorder_blocks,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slugs=["block-2", "block-1"],
        )
        self.assertResponse(
            response, error="ValueError: slugs does not have the expected elements"
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_set_block_markdown(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, has_custom_report=True)  # tab-1
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        response = self.run_handler(
            set_block_markdown,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-1",
            markdown="bar",
        )
        self.assertResponse(response, None)
        self.assertEqual(
            workflow.blocks.filter(slug="block-1", text_markdown="bar").exists(), True
        )

        send_update.assert_called()
        update = send_update.call_args[0][1]
        self.assertEqual(update.mutation_id, "mutation-1")

    def test_set_block_markdown_viewer_access_denied(self):
        workflow = Workflow.create_and_init(
            public=True, has_custom_report=True
        )  # tab-1
        workflow.blocks.create(
            position=0, slug="block-1", block_type="Text", text_markdown="foo"
        )

        response = self.run_handler(
            set_block_markdown,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-1",
            markdown="bar",
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_block_markdown_block_does_not_exist(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, has_custom_report=True)  # tab-1
        response = self.run_handler(
            set_block_markdown,
            user=user,
            mutationId="mutation-1",
            workflow=workflow,
            slug="block-1",
            markdown="bar",
        )
        self.assertResponse(
            response, error="DoesNotExist: Block matching query does not exist."
        )
