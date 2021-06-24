import asyncio
import datetime
import logging
from unittest.mock import Mock, patch

from dateutil.parser import isoparse
from django.contrib.auth.models import User
from django.test import override_settings

from cjworkbench.models.userprofile import UserProfile
from cjworkbench.models.userusage import UserUsage
from cjwstate import clientside, oauth, rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.commands import DeleteStep, SetStepParams
from cjwstate.models.fields import Role
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from server.handlers.step import (
    clear_file_upload_api_token,
    delete,
    delete_secret,
    fetch,
    generate_secret_access_token,
    get_file_upload_api_token,
    reset_file_upload_api_token,
    set_collapsed,
    set_notes,
    set_notifications,
    set_params,
    set_secret,
    set_stored_data_version,
    try_set_autofetch,
)

from .util import HandlerTestCase


async def async_noop(*args, **kwargs):
    pass


TestGoogleSecret = {
    "id_name": "google_credentials",
    "type": "secret",
    "secret_logic": {"provider": "oauth2", "service": "google"},
}


TestStringSecret = {
    "id_name": "string_secret",
    "type": "secret",
    "secret_logic": {
        "provider": "string",
        "label": "Secret",
        "pattern": r"\w\w\w",  # 'foo' is invalid; 'wrong' is not
        "placeholder": "Secret...",
        "help": "Help",
        "help_url": "https://example.org",
        "help_url_prompt": "Go",
    },
}


class StepTest(HandlerTestCase, DbTestCaseWithModuleRegistryAndMockKernel):
    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_params(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]}
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x", params={"foo": ""}
        )

        with self.assertLogs(level=logging.INFO):
            response = self.run_handler(
                set_params,
                user=user,
                workflow=workflow,
                stepId=step.id,
                values={"foo": "bar"},
            )
        self.assertResponse(response, data=None)

        delta = workflow.deltas.filter(command_name=SetStepParams.__name__).first()
        self.assertEquals(delta.values_for_forward, {"params": {"foo": "bar"}})
        self.assertEquals(delta.values_for_backward, {"params": {"foo": ""}})
        self.assertEquals(delta.step_id, step.id)
        step.refresh_from_db()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_params_invalid_params(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]}
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x", params={"foo": ""}
        )

        with self.assertLogs(level=logging.INFO):
            response = self.run_handler(
                set_params,
                user=user,
                workflow=workflow,
                stepId=step.id,
                values={"foo1": "bar"},
            )
        self.assertResponse(
            response,
            error=(
                "ValueError: Value {'foo': '', 'foo1': 'bar'} has wrong keys: "
                "expected frozenset({'foo'})"
            ),
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_params_null_byte_in_json(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "x", spec_kwargs={"parameters": [{"id_name": "foo", "type": "string"}]}
        )
        self.kernel.migrate_params.side_effect = lambda m, p: p
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x", params={"foo": ""}
        )

        with self.assertLogs(level=logging.INFO):
            response = self.run_handler(
                set_params,
                user=user,
                workflow=workflow,
                stepId=step.id,
                values={"foo": "b\x00\x00r"},
            )
        self.assertResponse(response, data=None)
        delta = workflow.deltas.last()
        self.assertEquals(delta.values_for_forward, {"params": {"foo": "br"}})

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_params_no_module(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", module_id_name="x"
        )

        response = self.run_handler(
            set_params,
            user=user,
            workflow=workflow,
            stepId=step.id,
            values={"foo": "bar"},
        )
        self.assertResponse(response, error="ValueError: Module x does not exist")

    def test_set_params_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            set_params,
            workflow=workflow,
            stepId=step.id,
            values={"foo": "bar"},
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_params_invalid_values(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            set_params,
            user=user,
            workflow=workflow,
            stepId=step.id,
            values="foobar",
        )  # String is not Dict
        self.assertResponse(response, error="BadRequest: values must be an Object")

    def test_set_params_invalid_step(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        step = other_workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            set_params,
            user=user,
            workflow=workflow,
            stepId=step.id,
            values={"foo": "bar"},
        )
        self.assertResponse(response, error="DoesNotExist: Step not found")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "send_user_update_to_user_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_delete(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            delete, user=user, workflow=workflow, stepId=step.id
        )
        self.assertResponse(response, data=None)

        delta = workflow.deltas.last()
        self.assertEquals(delta.command_name, DeleteStep.__name__)
        self.assertEquals(delta.step_id, step.id)
        step.refresh_from_db()
        self.assertEqual(step.is_deleted, True)

    def test_delete_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(delete, workflow=workflow, stepId=step.id)
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_delete_invalid_step(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        other_workflow = Workflow.create_and_init(owner=user)
        step = other_workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            delete, user=user, workflow=workflow, stepId=step.id
        )
        self.assertResponse(response, error="DoesNotExist: Step not found")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening", async_noop)
    def test_set_stored_data_version(self):
        version = "2018-12-12T21:30:00.000"
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        step.stored_objects.create(stored_at=isoparse(version), size=0)

        response = self.run_handler(
            set_stored_data_version,
            user=user,
            workflow=workflow,
            stepId=step.id,
            version=version,
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.stored_data_version, isoparse(version))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render_if_consumers_are_listening", async_noop)
    def test_set_stored_data_version_microsecond_date(self):
        version = "2018-12-12T21:30:00.000123Z"  # this is how "id" looks in JS
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        step.stored_objects.create(stored_at=isoparse(version), size=0)

        response = self.run_handler(
            set_stored_data_version,
            user=user,
            workflow=workflow,
            stepId=step.id,
            version=version,
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.stored_data_version, isoparse(version[:-1]))

    def test_set_stored_data_version_invalid_date(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            set_stored_data_version,
            user=user,
            workflow=workflow,
            stepId=step.id,
            version="not a date",
        )
        self.assertResponse(
            response, error="BadRequest: version must be an ISO8601 String"
        )

    def test_set_stored_data_version_viewer_access_denied(self):
        version = "2018-12-12T21:30:00.000"
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        step.stored_objects.create(stored_at=isoparse(version), size=0)

        response = self.run_handler(
            set_stored_data_version,
            workflow=workflow,
            stepId=step.id,
            version=version,
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_notes(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1", notes="A")

        response = self.run_handler(
            set_notes, user=user, workflow=workflow, stepId=step.id, notes="B"
        )
        self.assertResponse(response, data=None)

        delta = workflow.deltas.last()
        self.assertEquals(delta.values_for_forward, {"note": "B"})
        self.assertEquals(delta.values_for_backward, {"note": "A"})
        self.assertEquals(delta.step_id, step.id)
        self.assertEquals(delta.workflow_id, workflow.id)

        step.refresh_from_db()
        self.assertEqual(step.notes, "B")

    def test_set_notes_viewer_acces_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1", notes="A")

        response = self.run_handler(
            set_notes, workflow=workflow, stepId=step.id, notes="B"
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "queue_render", async_noop)
    def test_set_notes_forces_str(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1", notes="A")

        response = self.run_handler(
            set_notes,
            user=user,
            workflow=workflow,
            stepId=step.id,
            notes=["a", "b"],
        )
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.notes, "['a', 'b']")

    def test_set_collapsed(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", is_collapsed=False
        )

        response = self.run_handler(
            set_collapsed,
            user=user,
            workflow=workflow,
            stepId=step.id,
            isCollapsed=True,
        )
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.is_collapsed, True)

    def test_set_collapsed_viewer_acces_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", is_collapsed=False
        )

        response = self.run_handler(
            set_collapsed, workflow=workflow, stepId=step.id, isCollapsed=True
        )
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_set_collapsed_forces_bool(self):
        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", is_collapsed=False
        )

        # bool('False') is true
        response = self.run_handler(
            set_collapsed,
            user=user,
            workflow=workflow,
            stepId=step.id,
            isCollapsed="False",
        )
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.is_collapsed, True)

    @patch.object(rabbitmq, "queue_intercom_message")
    def test_set_notifications_to_false(self, queue_intercom_message):
        queue_intercom_message.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", notifications=True
        )

        response = self.run_handler(
            set_notifications,
            user=user,
            workflow=workflow,
            stepId=step.id,
            notifications=False,
        )
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.notifications, False)
        queue_intercom_message.assert_not_called()  # only log if setting to true

    @patch.object(rabbitmq, "queue_intercom_message")
    def test_set_notifications(self, queue_intercom_message):
        queue_intercom_message.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            order=0, slug="step-1", notifications=False
        )

        response = self.run_handler(
            set_notifications,
            user=user,
            workflow=workflow,
            stepId=step.id,
            notifications=True,
        )
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.notifications, True)
        queue_intercom_message.assert_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "send_user_update_to_user_clients")
    def test_try_set_autofetch_happy_path(self, update_user, update_workflow):
        update_user.side_effect = async_noop
        update_workflow.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user)
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(
            try_set_autofetch,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
            isAutofetch=True,
            fetchInterval=19200,
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, True)
        self.assertEqual(step.update_interval, 19200)
        self.assertLess(
            step.next_update,
            datetime.datetime.now() + datetime.timedelta(seconds=19202),
        )
        self.assertGreater(
            step.next_update,
            datetime.datetime.now() + datetime.timedelta(seconds=19198),
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.fetches_per_day, 4.5)

        update_user.assert_called_with(
            user.id, clientside.UserUpdate(usage=UserUsage(fetches_per_day=4.5))
        )
        update_workflow.assert_called_with(
            workflow.id,
            clientside.Update(
                workflow=clientside.WorkflowUpdate(fetches_per_day=4.5),
                steps={
                    step.id: clientside.StepUpdate(
                        is_auto_fetch=True, fetch_interval=19200
                    )
                },
            ),
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "send_user_update_to_user_clients")
    def test_try_set_autofetch_disable_autofetch(self, update_user, update_workflow):
        update_user.side_effect = async_noop
        update_workflow.side_effect = async_noop

        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user)
        workflow = Workflow.create_and_init(owner=user, fetches_per_day=72.0)
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=1200,
            next_update=datetime.datetime.now(),
        )

        response = self.run_handler(
            try_set_autofetch,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
            isAutofetch=False,
            fetchInterval=300,
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, False)
        self.assertEqual(step.update_interval, 300)
        self.assertIsNone(step.next_update)
        workflow.refresh_from_db()
        self.assertEqual(workflow.fetches_per_day, 0.0)

        update_workflow.assert_called_with(
            workflow.id,
            clientside.Update(
                workflow=clientside.WorkflowUpdate(fetches_per_day=0.0),
                steps={
                    step.id: clientside.StepUpdate(
                        is_auto_fetch=False, fetch_interval=300
                    )
                },
            ),
        )
        update_user.assert_called_with(
            user.id, clientside.UserUpdate(usage=UserUsage(fetches_per_day=0.0))
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "send_user_update_to_user_clients")
    def test_try_set_autofetch_exceed_quota(self, update_user, update_workflow):
        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user, max_fetches_per_day=10)
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")
        response = self.run_handler(
            try_set_autofetch,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
            isAutofetch=True,
            fetchInterval=300,
        )
        self.assertEqual(response.error, "AutofetchQuotaExceeded")
        step.refresh_from_db()
        self.assertEqual(step.auto_update_data, False)
        workflow.refresh_from_db()
        self.assertEqual(workflow.fetches_per_day, 0.0)

        update_user.assert_not_called()
        update_workflow.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(rabbitmq, "send_user_update_to_user_clients", async_noop)
    def test_try_set_autofetch_allow_exceed_quota_when_reducing(self):
        user = User.objects.create(username="a", email="a@example.org")
        UserProfile.objects.create(user=user, max_fetches_per_day=10)
        workflow = Workflow.create_and_init(owner=user, fetches_per_day=288.0)
        step = workflow.tabs.first().steps.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            update_interval=300,
            next_update=datetime.datetime.now(),
        )
        response = self.run_handler(
            try_set_autofetch,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
            isAutofetch=True,
            fetchInterval=600,
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.update_interval, 600)
        workflow.refresh_from_db()
        self.assertEqual(workflow.fetches_per_day, 144.0)

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    @patch.object(rabbitmq, "queue_fetch")
    def test_fetch(self, queue_fetch, send_update):
        future_none = asyncio.Future()
        future_none.set_result(None)

        queue_fetch.return_value = future_none
        send_update.return_value = future_none

        user = User.objects.create(username="a", email="a@example.org")
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(fetch, user=user, workflow=workflow, stepId=step.id)
        self.assertResponse(response, data=None)

        step.refresh_from_db()
        self.assertEqual(step.is_busy, True)
        queue_fetch.assert_called_with(workflow.id, step.id)
        send_update.assert_called_with(
            workflow.id,
            clientside.Update(steps={step.id: clientside.StepUpdate(is_busy=True)}),
        )

    def test_fetch_viewer_access_denied(self):
        workflow = Workflow.create_and_init(public=True)
        step = workflow.tabs.first().steps.create(order=0, slug="step-1")

        response = self.run_handler(fetch, workflow=workflow, stepId=step.id)
        self.assertResponse(response, error="AuthError: no write access to workflow")

    def test_generate_secret_access_token_editor_access_denied(self):
        user = User.objects.create(email="write@example.org")
        workflow = Workflow.create_and_init(public=True)
        workflow.acl.create(email=user.email, role=Role.EDITOR)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets", order=0, slug="step-1"
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, error="AuthError: no owner access to workflow")

    def test_generate_secret_access_token_no_value_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            slug="step-1",
            order=0,
            secrets={"google_credentials": None},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, data={"token": None})

    def test_generate_secret_access_token_wrong_param_type_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            params={"s": '{"name":"a","secret":"hello"}'},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="a",
        )
        self.assertResponse(response, data={"token": None})

    def test_generate_secret_access_token_wrong_param_name_gives_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="twitter_credentials",
        )
        self.assertResponse(response, data={"token": None})

    @patch("cjwstate.oauth.OAuthService.lookup_or_none", lambda _: None)
    @override_settings(OAUTH_SERVICES={"twitter": {}})
    def test_generate_secret_access_token_no_service_gives_error(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, error=("AuthError: we only support twitter"))

    @patch("cjwstate.oauth.OAuthService.lookup_or_none")
    def test_generate_secret_access_token_auth_error_gives_error(self, factory):
        service = Mock(oauth.OAuth2)
        service.generate_access_token_or_str_error.return_value = "an error"
        factory.return_value = service

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, error="AuthError: an error")

    @patch("cjwstate.oauth.OAuthService.lookup_or_none")
    def test_generate_secret_access_token_happy_path(self, factory):
        service = Mock(oauth.OAuth2)
        service.generate_access_token_or_str_error.return_value = {
            "access_token": "a-token",
            "refresh_token": "something we must never share",
        }
        factory.return_value = service

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            generate_secret_access_token,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, data={"token": "a-token"})

    def test_delete_secret_editor_access_denied(self):
        user = User.objects.create(email="write@example.org")
        workflow = Workflow.create_and_init(public=True)
        workflow.acl.create(email=user.email, role=Role.EDITOR)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            delete_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, error="AuthError: no owner access to workflow")

    def test_delete_secret_ignore_non_secret(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            params={"foo": "bar"},
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            delete_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="foo",
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.params, {"foo": "bar"})
        self.assertEqual(
            step.secrets, {"google_credentials": {"name": "a", "secret": "hello"}}
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_delete_secret_happy_path(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "googlesheets", spec_kwargs={"parameters": [TestGoogleSecret]}
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="googlesheets",
            order=0,
            slug="step-1",
            secrets={"google_credentials": {"name": "a", "secret": "hello"}},
        )

        response = self.run_handler(
            delete_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="google_credentials",
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.secrets, {})

        send_update.assert_called()
        delta = send_update.call_args[0][1]
        self.assertEqual(delta.steps[step.id].secrets, {})

    def test_set_secret_editor_access_denied(self):
        user = User.objects.create(email="write@example.org")
        workflow = Workflow.create_and_init(public=True)
        workflow.acl.create(email=user.email, role=Role.EDITOR)
        create_module_zipfile("g", spec_kwargs={"parameters": [TestStringSecret]})
        step = workflow.tabs.first().steps.create(
            module_id_name="g", order=0, slug="step-1"
        )
        response = self.run_handler(
            set_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="string_secret",
            secret="foo",
        )
        self.assertResponse(response, error="AuthError: no owner access to workflow")

    def test_set_secret_error_not_a_secret(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile(
            "g",
            spec_kwargs={
                "parameters": [{"id_name": "string_secret", "type": "string"}]
            },
        )
        step = workflow.tabs.first().steps.create(
            module_id_name="g",
            order=0,
            slug="step-1",
            params={"string_secret": "bar"},
            secrets={},
        )

        response = self.run_handler(
            set_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="string_secret",
            secret="foo",
        )
        self.assertResponse(
            response, error="BadRequest: param is not a secret string parameter"
        )
        step.refresh_from_db()
        self.assertEqual(step.params, {"string_secret": "bar"})
        self.assertEqual(step.secrets, {})

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_set_secret_happy_path(self, send_update):
        send_update.side_effect = async_noop

        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        create_module_zipfile("g", spec_kwargs={"parameters": [TestStringSecret]})
        step = workflow.tabs.first().steps.create(
            module_id_name="g", order=0, slug="step-1"
        )

        response = self.run_handler(
            set_secret,
            user=user,
            workflow=workflow,
            stepId=step.id,
            param="string_secret",
            secret="foo",
        )
        self.assertResponse(response, data=None)
        step.refresh_from_db()
        self.assertEqual(step.secrets["string_secret"]["secret"], "foo")
        self.assertIsInstance(step.secrets["string_secret"]["name"], str)

        send_update.assert_called()
        delta = send_update.call_args[0][1]
        self.assertEqual(
            delta.steps[step.id].secrets,
            {"string_secret": {"name": step.secrets["string_secret"]["name"]}},
        )

    def test_get_file_upload_api_token(self):
        # Currently, we don't restrict this API to just "upload" modules. We do
        # restrict the actual _uploads_, so this oversight isn't a big deal.
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        workflow.tabs.first().steps.create(
            module_id_name="x", order=0, slug="step-1", file_upload_api_token="abcd1234"
        )
        response = self.run_handler(
            get_file_upload_api_token,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
        )
        self.assertResponse(response, data={"apiToken": "abcd1234"})

    def test_get_file_upload_api_token_null(self):
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        workflow.tabs.first().steps.create(
            module_id_name="x", order=0, slug="step-1", file_upload_api_token=None
        )
        response = self.run_handler(
            get_file_upload_api_token,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
        )
        self.assertResponse(response, data={"apiToken": None})

    def test_reset_file_upload_api_token(self):
        # Currently, we don't restrict this API to just "upload" modules. We do
        # restrict the actual _uploads_, so this oversight isn't a big deal.
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            module_id_name="x", order=0, slug="step-1"
        )
        response = self.run_handler(
            reset_file_upload_api_token,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
        )
        step.refresh_from_db()
        self.assertEqual(
            len(step.file_upload_api_token), 43
        )  # 32 bytes, base64-encoded
        self.assertResponse(response, data={"apiToken": step.file_upload_api_token})

    def test_clear_file_upload_api_token(self):
        # Currently, we don't restrict this API to just "upload" modules. We do
        # restrict the actual _uploads_, so this oversight isn't a big deal.
        user = User.objects.create()
        workflow = Workflow.create_and_init(owner=user)
        step = workflow.tabs.first().steps.create(
            module_id_name="x", order=0, slug="step-1", file_upload_api_token="abcd1234"
        )
        response = self.run_handler(
            clear_file_upload_api_token,
            user=user,
            workflow=workflow,
            stepSlug="step-1",
        )
        step.refresh_from_db()
        self.assertResponse(response, data=None)
        self.assertIsNone(step.file_upload_api_token)
