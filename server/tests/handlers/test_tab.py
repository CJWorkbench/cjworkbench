from unittest.mock import patch
from django.contrib.auth.models import User
from server.handlers.tab import (
    add_module,
    reorder_modules,
    create,
    delete,
    duplicate,
    set_name,
)
from cjwstate import rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.commands import AddModuleCommand, ReorderModulesCommand
from .util import HandlerTestCase
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)


async def async_noop(*args, **kwargs):
    pass


def noop(*args, **kwargs):
    pass


class TabTest(HandlerTestCase, DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    @patch("server.utils.log_user_event_from_scope", noop)
    def test_add_module(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # with tab-1
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="slug-1",
            position=3,
            moduleIdName="amodule",
            paramValues={"foo": "bar"},
        )
        self.assertResponse(response, data=None)

        command = AddModuleCommand.objects.first()
        self.assertEquals(command.wf_module.order, 3)
        self.assertEquals(command.wf_module.module_id_name, "amodule")
        self.assertEquals(command.wf_module.params["foo"], "bar")
        self.assertEquals(command.wf_module.tab.slug, "tab-1")
        self.assertEquals(command.workflow_id, workflow.id)

    def test_add_module_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)  # tab-1
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )
        response = self.run_handler(
            add_module,
            workflow=workflow,
            tabSlug="tab-1",
            slug="step-1",
            position=3,
            moduleIdName="amodule",
            paramValues={"foo": "bar"},
        )

        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_add_module_param_values_not_object(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="step-1",
            position=3,
            moduleIdName="amodule",
            paramValues="foobar",
        )
        self.assertResponse(response, error="BadRequest: paramValues must be an Object")

    def test_add_module_invalid_param_values(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="step-1",
            position=3,
            moduleIdName="amodule",
            paramValues={"foo": 3},
        )
        self.assertResponse(
            response,
            error=("BadRequest: param validation failed: Value 3 is not a string"),
        )

    def test_add_module_invalid_position(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="step-1",
            position="foo",
            moduleIdName="amodule",
            paramValues={"foo": "bar"},
        )
        self.assertResponse(response, error="BadRequest: position must be a Number")

    def test_add_module_missing_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        # Create a "honeypot" tab -- make sure the module doesn't get inserted
        # in the other workflow's 'tab-2'!
        other_workflow.tabs.create(position=1, slug="tab-2")
        create_module_zipfile(
            "amodule",
            spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]},
        )

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-2",
            slug="step-1",
            position=3,
            moduleIdName="amodule",
            paramValues={"foo": "bar"},
        )
        self.assertResponse(response, error="DoesNotExist: Tab not found")

    def test_add_module_missing_module_version(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1

        response = self.run_handler(
            add_module,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="step-1",
            position=3,
            moduleIdName="notamodule",
            paramValues={"foo": "bar"},
        )
        self.assertResponse(response, error="BadRequest: module does not exist")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_reorder_modules(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        tab = workflow.tabs.first()  # tab-1
        step1 = tab.wf_modules.create(order=0, slug="step-1")
        step2 = tab.wf_modules.create(order=1, slug="step-2")

        response = self.run_handler(
            reorder_modules,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            wfModuleIds=[step2.id, step1.id],
        )
        self.assertResponse(response, data=None)

        command = ReorderModulesCommand.objects.first()
        self.assertEquals(command.tab_id, tab.id)
        self.assertEquals(command.workflow_id, workflow.id)

    def test_reorder_modules_viewer_denied_access(self):
        workflow = Workflow.create_and_init(public=True)
        tab = workflow.tabs.first()  # tab-1
        step1 = tab.wf_modules.create(order=0, slug="step-1")
        step2 = tab.wf_modules.create(order=1, slug="step-2")

        response = self.run_handler(
            reorder_modules,
            workflow=workflow,
            tabSlug="tab-1",
            wfModuleIds=[step2.id, step1.id],
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_reorder_modules_invalid_wf_module_ids(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()  # tab-1
        step1 = tab.wf_modules.create(order=0, slug="step-1")
        step2 = tab.wf_modules.create(order=1, slug="step-2")

        response = self.run_handler(
            reorder_modules,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            wfModuleIds=[step2.id, step1.id, 2],
        )
        self.assertResponse(
            response, error="new_order does not have the expected elements"
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_create(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)

        response = self.run_handler(
            create, user=user, workflow=workflow, slug="tab-ab13", name="Foo"
        )
        self.assertResponse(response, data=None)
        self.assertEqual(workflow.live_tabs.count(), 2)
        self.assertEqual(workflow.live_tabs.last().name, "Foo")
        self.assertEqual(workflow.live_tabs.last().slug, "tab-ab13")

    def test_create_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        response = self.run_handler(create, workflow=workflow)
        self.assertResponse(response, error="AuthError: no write access to workflow")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_delete(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        tab2 = workflow.tabs.create(position=1, slug="tab-2")

        response = self.run_handler(
            delete, user=user, workflow=workflow, tabSlug="tab-2"
        )
        self.assertResponse(response, data=None)
        self.assertEqual(workflow.live_tabs.count(), 1)
        tab2.refresh_from_db()
        self.assertTrue(tab2.is_deleted)

    def test_delete_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        workflow.tabs.create(position=1, slug="tab-2")
        response = self.run_handler(delete, workflow=workflow, tabSlug="tab-2")
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_delete_missing_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        response = self.run_handler(
            delete, user=user, workflow=workflow, tabSlug="tab-2"
        )
        self.assertResponse(response, error="DoesNotExist: Tab not found")

    def test_delete_last_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        response = self.run_handler(
            delete, user=user, workflow=workflow, tabSlug="tab-1"
        )
        # No-op
        self.assertResponse(response, data=None)
        self.assertEqual(workflow.live_tabs.count(), 1)

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_duplicate(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        response = self.run_handler(
            duplicate,
            user=user,
            workflow=workflow,
            tabSlug="tab-1",
            slug="tab-2",
            name="Tab 2",
        )
        self.assertResponse(response, data=None)
        self.assertEqual(workflow.live_tabs.count(), 2)
        tab2 = workflow.live_tabs.last()
        self.assertEqual(tab2.slug, "tab-2")

    def test_duplicate_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        workflow.tabs.create(position=1, slug="tab-2")
        response = self.run_handler(
            duplicate, workflow=workflow, tabSlug="tab-1", slug="tab-2", name="Tab 2"
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_duplicate_missing_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        response = self.run_handler(
            duplicate,
            user=user,
            workflow=workflow,
            tabSlug="tab-missing",
            slug="tab-2",
            name="Tab 2",
        )
        self.assertResponse(response, error="DoesNotExist: Tab not found")

    def test_duplicate_tab_slug_conflict(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()
        workflow.tabs.create(position=1, slug="tab-2", name="Tab 2")
        response = self.run_handler(
            duplicate,
            user=user,
            workflow=workflow,
            tabSlug=tab.slug,
            slug="tab-2",
            name="Tab 2",
        )
        self.assertResponse(
            response, error='BadRequest: tab slug "tab-2" is already used'
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    def test_set_name(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        tab = workflow.tabs.first()  # tab-1

        response = self.run_handler(
            set_name, user=user, workflow=workflow, tabSlug="tab-1", name="B"
        )
        self.assertResponse(response, data=None)
        tab.refresh_from_db()
        self.assertEqual(tab.name, "B")

    def test_set_name_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)  # tab-1
        response = self.run_handler(
            set_name, workflow=workflow, tabSlug="tab-1", name="B"
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_name_missing_tab(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)  # tab-1
        response = self.run_handler(
            set_name, user=user, workflow=workflow, tabSlug="tab-2", name="B"
        )
        self.assertResponse(response, error="DoesNotExist: Tab not found")
