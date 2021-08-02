import datetime
from unittest.mock import patch

from django.contrib.auth.models import User

from cjwstate import rabbitmq
from cjwstate.models import Workflow
from server.handlers.workflow import (
    begin_publish_dataset,
    set_name,
    set_position,
    set_tab_order,
    set_selected_tab,
)
from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


class WorkflowTest(HandlerTestCase):
    @patch.object(rabbitmq, "queue_render")
    def test_begin_publish_dataset(self, queue_render):
        queue_render.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user,
            name="A",
            dataset_readme_md="Readme",
            updated_at=datetime.datetime(2021, 7, 27, 18, 1, 2, 123456),
        )
        workflow.tabs.update(is_in_dataset=True)

        response = self.run_handler(
            begin_publish_dataset,
            user=user,
            workflow=workflow,
            requestId="req-1",
            workflowUpdatedAt="2021-07-27T18:01:02.123456Z",
        )
        queue_render.assert_called_with(
            workflow.id,
            workflow.last_delta_id,
            rabbitmq.PublishDatasetSpec(
                request_id="req-1",
                workflow_name="A",
                readme_md="Readme",
                tab_slugs=["tab-1"],
            ),
        )
        self.assertResponse(response, data=None)

    @patch.object(rabbitmq, "queue_render")
    def test_begin_publish_dataset_ignore_unincluded_tabs(self, queue_render):
        queue_render.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user,
            name="A",
            dataset_readme_md="Readme",
            updated_at=datetime.datetime(2021, 7, 27, 18, 1, 2, 123456),
        )
        workflow.tabs.create(position=1, slug="tab-2", is_in_dataset=True)
        workflow.tabs.create(position=2, slug="tab-3", is_in_dataset=False)

        response = self.run_handler(
            begin_publish_dataset,
            user=user,
            workflow=workflow,
            requestId="req-1",
            workflowUpdatedAt="2021-07-27T18:01:02.123456Z",
        )
        queue_render.assert_called_with(
            workflow.id,
            workflow.last_delta_id,
            rabbitmq.PublishDatasetSpec(
                request_id="req-1",
                workflow_name="A",
                readme_md="Readme",
                tab_slugs=["tab-2"],
            ),
        )
        self.assertResponse(response, data=None)

    def test_begin_publish_dataset_check_workflow_updated_at(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(
            owner=user,
            name="A",
            dataset_readme_md="Readme",
            updated_at=datetime.datetime(2021, 7, 27, 18, 1, 2, 123456),
        )
        workflow.tabs.update(is_in_dataset=True)

        # Send a request with the wrong updated_at
        response = self.run_handler(
            begin_publish_dataset,
            user=user,
            workflow=workflow,
            requestId="req-1",
            workflowUpdatedAt="2021-07-21T18:01:01.111111",
        )
        self.assertResponse(response, error="updated-at-mismatch")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_name(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="A")

        response = self.run_handler(set_name, user=user, workflow=workflow, name="B")
        self.assertResponse(response, data=None)

        delta = workflow.deltas.last()
        self.assertEqual(delta.values_for_forward, {"title": "B"})
        self.assertEqual(delta.values_for_backward, {"title": "A"})

        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "B")

    def test_set_name_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)

        response = self.run_handler(set_name, workflow=workflow, name="B")
        self.assertResponse(response, error="AuthError: no write access to workflow")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_name_coerce_to_str(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user, name="A")

        response = self.run_handler(
            set_name, user=user, workflow=workflow, name=["B", {"x": "y"}]
        )
        self.assertResponse(response, data=None)

        workflow.refresh_from_db()
        self.assertEqual(workflow.name, "['B', {'x': 'y'}]")

    def test_set_position(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        tab2 = workflow.tabs.create(position=1)
        tab2.steps.create(order=0, slug="step-1")
        tab2.steps.create(order=1, slug="step-2")
        step = tab2.steps.create(order=2, slug="step-3")

        response = self.run_handler(
            set_position, user=user, workflow=workflow, stepId=step.id
        )
        self.assertResponse(response, data=None)

        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)
        tab2.refresh_from_db()
        self.assertEqual(tab2.selected_step_position, 2)

    def test_set_position_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(set_position, workflow=workflow, stepId=step.id)
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_position_ignore_other_workflow(self):
        # (Also tests "ignore missing Step")
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)

        workflow2 = Workflow.create_and_init(owner=user)
        tab2 = workflow2.tabs.first()
        tab2.steps.create(order=0, slug="step-1")  # dummy first step (selected)
        step = tab2.steps.create(order=1, slug="step-2")  # step we'll "select"
        tab2.selected_step_position = 0
        tab2.save(update_fields=["selected_step_position"])

        response = self.run_handler(
            set_position, user=user, workflow=workflow, stepId=step.id
        )
        self.assertResponse(response, data=None)  # we ignore missing steps
        # Nothing should be written to workflow2. Also, there's nothing to
        # write to workflow. So nothing in the DB should have changed.
        #
        # We don't report an error because there's a race: Alice deletes
        # module, and Bob clicks it as Alice is deleting it. We want to ignore
        # Bob's action in that case.
        tab2.refresh_from_db()
        self.assertEqual(tab2.selected_step_position, 0)

    def test_set_selected_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_selected_tab, user=user, workflow=workflow, tabSlug="tab-2"
        )
        self.assertResponse(response, data=None)

        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_tab_position, 1)

    def test_set_selected_tab_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_selected_tab, workflow=workflow, tabSlug="tab-2"
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_selected_tab_ignore_other_workflow(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)

        workflow2 = Workflow.create_and_init(owner=user)
        workflow2.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_selected_tab, user=user, workflow=workflow, tabSlug="tab-2"
        )
        self.assertResponse(response, error="Invalid tab slug")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_tab_order(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # initial tab: tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_tab_order, user=user, workflow=workflow, tabSlugs=["tab-2", "tab-1"]
        )
        self.assertResponse(response, data=None)

        self.assertEqual(
            list(workflow.live_tabs.values_list("slug", flat=True)), ["tab-2", "tab-1"]
        )

    def test_set_tab_order_viewer_access_denied(self):
        workflow = Workflow.create_and_init()  # tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_tab_order, workflow=workflow, tabSlugs=["tab-2", "tab-1"]
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_tab_order_wrong_tab_slugs(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            set_tab_order, user=user, workflow=workflow, tabSlugs=["tab-3", "tab-2"]
        )
        self.assertResponse(response, error="wrong tab slugs")

    def test_set_tab_order_invalid_tab_ids(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)

        response = self.run_handler(
            set_tab_order, user=user, workflow=workflow, tabSlugs=[1, 2]
        )
        self.assertResponse(response, error="tabSlugs must be an Array of slugs")
