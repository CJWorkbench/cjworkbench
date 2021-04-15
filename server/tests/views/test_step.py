import json
import re
from datetime import datetime as dt
from http import HTTPStatus as status
from unittest.mock import patch

import pyarrow as pa
from cjwmodule.arrow.testing import make_table, make_column
from django.test import override_settings

import cjwstate.modules
from cjwstate import commands, rabbitmq
from cjwstate.models import Workflow
from cjwstate.models.fields import Role
from cjwstate.rendercache.io import delete_parquet_files_for_step
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
    create_test_user,
)


async def async_noop(*args, **kwargs):
    pass


def read_streaming_json(response):
    return json.loads(b"".join(response.streaming_content))


@patch.object(rabbitmq, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class StepViewTestCase(DbTestCaseWithModuleRegistryAndMockKernel):
    """Logged in, logging disabled, rabbitmq/commands disabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cjwstate.modules.init_module_system()  # create module tempdir

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super().setUp()

        self.user = create_test_user()
        self.client.force_login(self.user)

        self.log_patcher = patch("server.utils.log_user_event_from_request")
        self.log_patch = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()
        super().tearDown()


class RenderTableSliceTest(StepViewTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )
        self.step2 = self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=2
        )

    def _request_step(self, step, query_string=""):
        return self.client.get(
            "/workflows/%d/steps/%s/delta-%d/result-table-slice.json%s"
            % (self.workflow.id, step.slug, step.last_relevant_delta_id, query_string)
        )

    # Test some json conversion gotchas we encountered during development
    def test_pandas_13258(self):
        # simple test case where Pandas produces int64 column type, and json
        # conversion throws ValueError
        # https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257
        int64 = 2 ** 62 + 10
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [1], pa.int64())),
        )
        self.step2.save()

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)

    @override_settings(MAX_COLUMNS_PER_CLIENT_REQUEST=2)
    def test_max_columns_returned(self):
        # Only at most MAX_COLUMNS_PER_CLIENT_REQUEST should be returned,
        # since we do not display more than that. (This is a funky hack that
        # assumes the client will behave differently when it has >MAX columns.)
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(
                make_column("A", [1]),
                make_column("B", [2]),
                make_column("C", [3]),
                make_column("D", [4]),
            ),
        )

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)
        # One column more than configured limit, so client knows to display
        # "too many columns".
        self.assertEqual(len(read_streaming_json(response)[0]), 3)

    def test_data(self):
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(
                make_column("Class", ["math", "english", "history", "economics"]),
                make_column("M", [10, None, 11, 20], pa.float64()),
                make_column("F", [12, 7, 13, 20]),
            ),
        )

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            read_streaming_json(response),
            [
                {"Class": "math", "F": 12, "M": 10.0},
                {"Class": "english", "F": 7, "M": None},
                {"Class": "history", "F": 13, "M": 11.0},
                {"Class": "economics", "F": 20, "M": 20.0},
            ],
        )

    def test_auth_report_viewer_denied(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.client.force_login(user)
        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 403)

    def test_auth_viewer_allowed(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.VIEWER)
        self.client.force_login(user)
        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)

    def test_auth_editor_allowed(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.EDITOR)
        self.client.force_login(user)
        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)

    def test_auth_user_without_acl_entry_not_allowed(self):
        user = create_test_user("alice", "alice@example.org")
        self.client.force_login(user)
        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 403)

    def test_auth_report_viewer_allowed_custom_report_table(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.workflow.has_custom_report = True
        self.workflow.save(update_fields=["has_custom_report"])
        self.workflow.blocks.create(
            position=0, slug="block-1", block_type="Table", tab_id=self.tab.id
        )
        self.client.force_login(user)
        response = self._request_step(self.step1)
        self.assertEqual(
            response.status_code, 403, "Should not have access to not-last step of tab"
        )
        response = self._request_step(self.step2)
        self.assertEqual(
            response.status_code, 200, "Should have access to last step of tab"
        )

    def test_auth_report_viewer_denied_custom_report_chart(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.workflow.has_custom_report = True
        self.workflow.save(update_fields=["has_custom_report"])
        self.workflow.blocks.create(
            position=0, slug="block-1", block_type="Chart", step_id=self.step1.id
        )
        self.client.force_login(user)
        response = self._request_step(self.step1)
        self.assertEqual(
            response.status_code, 403, "Should not have access to table data"
        )
        response = self._request_step(self.step2)
        self.assertEqual(
            response.status_code,
            403,
            "Should not have access to non-reported Chart step",
        )

    def test_auth_report_viewer_denied_auto_report_chart(self):
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.client.force_login(user)
        create_module_zipfile("chart", spec_kwargs={"html_output": True})
        create_module_zipfile("notchart", spec_kwargs={"html_output": False})
        self.step1.module_id_name = "chart"
        self.step1.save(update_fields=["module_id_name"])
        self.step2.module_id_name = "notchart"
        self.step2.save(update_fields=["module_id_name"])
        response = self._request_step(self.step1)
        self.assertEqual(
            response.status_code, 403, "Should not have access to table data"
        )
        response = self._request_step(self.step2)
        self.assertEqual(
            response.status_code, 403, "Should not have access to non-Chart step"
        )

    def test_null_timestamp(self):
        # Ran into problems 2019-09-06, when switching to Arrow
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [dt(2019, 1, 2, 3, 4, 5, 6007, None), None])),
        )

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            read_streaming_json(response),
            [{"A": "2019-01-02T03:04:05.006007Z"}, {"A": None}],
        )

    def test_missing_parquet_file(self):
        # https://www.pivotaltracker.com/story/show/161988744
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [1])),
        )

        # Simulate a race: we're overwriting the cache or deleting the Step
        # or some-such.
        delete_parquet_files_for_step(self.workflow.id, self.step2.id)

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

    def test_only_rows(self):
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [0, 1, 2, 3, 4])),
        )

        response = self._request_step(self.step2, "?startrow=1&endrow=3")
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(read_streaming_json(response), [{"A": 1}, {"A": 2}])

    def test_clip_out_of_bounds(self):
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [0, 1])),
        )

        # index out of bounds should clip
        response = self._request_step(self.step2, "?startrow=-1&endrow=500")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(read_streaming_json(response), [{"A": 0}, {"A": 1}])

    def test_start_row_after_end_row(self):
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id,
            make_table(make_column("A", [0, 1, 2, 3, 4])),
        )

        response = self._request_step(self.step2, "?startrow=3&endrow=1")
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(read_streaming_json(response), [])

    def test_invalid_endrow(self):
        # index not a number -> bad request
        response = self._request_step(self.step2, "?startrow=0&endrow=frog")
        self.assertEqual(response.status_code, status.BAD_REQUEST)

    def test_wrong_cached_delta_id(self):
        write_to_rendercache(
            self.workflow,
            self.step2,
            self.step2.last_relevant_delta_id - 1,
            make_table(make_column("A", [1])),
        )

        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(json.loads(response.content), [])

    def test_delta_not_cached(self):
        response = self._request_step(self.step2)
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(json.loads(response.content), [])


class EmbedTest(StepViewTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create(
            name="test", owner=self.user, last_delta_id=1
        )
        self.tab = self.workflow.tabs.create(position=0)
        self.step = self.tab.steps.create(
            order=0, module_id_name="chart", slug="step-1", last_relevant_delta_id=1
        )

    def _request(self):
        return self.client.get("/workflows/%d/steps/step-1/embed" % self.workflow.id)

    def test_deny_secret_link(self):
        self.workflow.public = False
        self.workflow.secret_id = "wsecret"
        self.workflow.save(update_fields=["public", "secret_id"])
        self.client.logout()

        response = self.client.get("/workflows/wsecret/steps/step-1/embed")

        # NOT_FOUND because secret URLs aren't even routed
        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_missing_module_is_404(self):
        response = self._request()

        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_missing_module_html_is_404(self):
        create_module_zipfile("chart", spec_kwargs={"html_output": False})

        response = self._request()

        self.assertEqual(response.status_code, status.NOT_FOUND)

    def test_init_state(self):
        create_module_zipfile("chart", spec_kwargs={"html_output": True}, html="hi")
        write_to_rendercache(
            self.workflow, self.step, 1, make_table(make_column("A", [1])), json={}
        )

        with self.assertLogs("cjwstate.params", level="INFO"):
            response = self._request()

        self.assertEqual(response.status_code, status.OK)
        init_state_match = re.search(br"window.initState =([^\n]*)", response.content)
        init_state = json.loads(init_state_match.group(1))
        self.assertEqual(init_state["workflow"]["id"], self.workflow.id)
        self.assertEqual(init_state["step"]["module"], "chart")
        self.assertEqual(init_state["step"]["slug"], "step-1")

    @patch.object(rabbitmq, "queue_render")
    def test_missing_cached_response_sends_503(self, queue_render):
        queue_render.side_effect = async_noop
        create_module_zipfile(
            "chart", spec_kwargs={"html_output": True}, html="hi", version="develop"
        )
        write_to_rendercache(
            self.workflow, self.step, 1, make_table(make_column("A", [1])), json={}
        )
        self.step.last_relevant_delta_id = 2
        self.step.save(update_fields=["last_relevant_delta_id"])
        self.workflow.last_delta_id = 3
        self.workflow.save(update_fields=["last_delta_id"])

        with self.assertLogs(
            "cjwstate.params", level="INFO"
        ):  # migrate_params() from jsonize
            with self.assertLogs("django.request", level="ERROR"):  # 503
                response = self._request()

        self.assertEqual(response.status_code, status.SERVICE_UNAVAILABLE)
        self.assertIn(b"window.location.reload()", response.content)
        queue_render.assert_called_with(self.workflow.id, 3)


class ResultColumnValueCountsTest(StepViewTestCase):
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )

    def _request(self, column: str):
        return self.client.get(
            "/workflows/%d/steps/%s/delta-%d/result-column-value-counts.json?column=%s"
            % (
                self.workflow.id,
                self.step1.slug,
                self.step1.last_relevant_delta_id,
                column,
            )
        )

    def test_str(self):
        write_to_rendercache(
            self.workflow,
            self.step1,
            self.step1.last_relevant_delta_id,
            make_table(make_column("A", ["a", "b", "b", "a", "c", None])),
        )

        response = self._request("A")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content), {"values": {"a": 2, "b": 2, "c": 1}}
        )

    def test_dictionary(self):
        write_to_rendercache(
            self.workflow,
            self.step1,
            self.step1.last_relevant_delta_id,
            make_table(
                make_column("A", ["a", "b", "b", "a", "c", None], dictionary=True)
            ),
        )

        response = self._request("A")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content), {"values": {"a": 2, "b": 2, "c": 1}}
        )

    def test_corrupt_cache(self):
        # https://www.pivotaltracker.com/story/show/161988744
        write_to_rendercache(
            self.workflow,
            self.step1,
            self.step1.last_relevant_delta_id,
            make_table(make_column("A", ["a"])),
        )
        # Simulate a race: we're overwriting the cache or deleting the Step
        # or some-such.
        delete_parquet_files_for_step(self.workflow.id, self.step1.id)

        response = self._request("A")

        # We _could_ return an empty result set; but our only goal here is
        # "don't crash" and this 404 seems to be the simplest implementation.
        # (We assume that if the data is deleted, the user has moved elsewhere
        # and this response is going to be ignored.)
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": 'column "A" not found'}
        )

    def test_disallow_non_text(self):
        write_to_rendercache(
            self.workflow,
            self.step1,
            self.step1.last_relevant_delta_id,
            make_table(make_column("A", [1, 2, 3, 2, 1])),
        )

        response = self._request("A")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"values": {}})

    def test_missing_column_param(self):
        response = self.client.get(
            "/workflows/%d/steps/%s/delta-%d/result-column-value-counts.json"
            % (self.workflow.id, self.step1.slug, self.step1.last_relevant_delta_id),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content), {"error": 'Missing a "column" parameter'}
        )

    def test_wrong_column(self):
        write_to_rendercache(
            self.workflow,
            self.step1,
            self.step1.last_relevant_delta_id,
            make_table(make_column("A", ["a"])),
        )

        response = self._request("B")

        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": 'column "B" not found'}
        )


class ResultJsonTest(StepViewTestCase):
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.step = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )

    def _request(self):
        return self.client.get(
            "/workflows/%d/steps/%s/delta-%d/result-json.json"
            % (self.workflow.id, self.step.slug, self.step.last_relevant_delta_id)
        )

    def test_cached_result_has_wrong_delta_id(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            make_table(make_column("A", [1])),
            json={"hello": "world"},
        )
        self.step.last_relevant_delta_id = 3
        self.step.save(update_fields=["last_relevant_delta_id"])

        response = self._request()

        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": "render result not in cache"}
        )

    def test_json(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            make_table(make_column("A", [1])),
            json={"hello": "world!"},
        )

        response = self._request()

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(json.loads(response.content), {"hello": "world!"})

    def test_empty_json(self):
        write_to_rendercache(
            self.workflow, self.step, 1, make_table(make_column("A", [1])), json={}
        )

        response = self._request()

        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": "render result has no JSON"}
        )

    def test_auth_report_viewer_denied_custom_report_table(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            make_table(make_column("A", [1])),
            json={"hello": "world!"},
        )
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.workflow.has_custom_report = True
        self.workflow.save(update_fields=["has_custom_report"])
        self.workflow.blocks.create(
            position=0, slug="block-1", block_type="Table", tab_id=self.tab.id
        )
        self.client.force_login(user)
        response = self._request()
        self.assertEqual(
            response.status_code, 403, "Table access does not imply Chart access"
        )

    def test_auth_report_viewer_allowed_custom_report_chart(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            make_table(make_column("A", [1])),
            json={"hello": "world!"},
        )
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.workflow.has_custom_report = True
        self.workflow.save(update_fields=["has_custom_report"])
        self.workflow.blocks.create(
            position=0, slug="block-1", block_type="Chart", step_id=self.step.id
        )
        self.client.force_login(user)
        response = self._request()
        self.assertEqual(response.status_code, 200, "Should have access to Chart step")

    def test_auth_report_viewer_allowed_auto_report_chart(self):
        write_to_rendercache(
            self.workflow,
            self.step,
            1,
            make_table(make_column("A", [1])),
            json={"hello": "world!"},
        )
        user = create_test_user("alice", "alice@example.org")
        self.workflow.acl.create(email="alice@example.org", role=Role.REPORT_VIEWER)
        self.client.force_login(user)
        create_module_zipfile("chart", spec_kwargs={"html_output": True})
        self.step.module_id_name = "chart"
        self.step.save(update_fields=["module_id_name"])
        response = self._request()
        self.assertEqual(response.status_code, 200, "Should have access to Chart step")


class TileTest(StepViewTestCase):
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )
        self.step2 = self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=2
        )

    def test_no_cached_result(self):
        response = self.client.get(
            f"/workflows/{self.workflow.id}/tiles/step-2/delta-2/0,0.json"
        )
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": "delta_id result not cached"}
        )

    def test_cached_result_has_wrong_delta_id(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", [1]))
        )
        self.step2.cached_render_result_delta_id = 3
        self.step2.last_relevant_delta_id = 3
        self.step2.save(
            update_fields=["cached_render_result_delta_id", "last_relevant_delta_id"]
        )

        response = self.client.get(
            f"/workflows/{self.workflow.id}/tiles/step-2/delta-2/0,0.json"
        )
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": "delta_id result not cached"}
        )

    def test_tile_row_out_of_bounds(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", [1]))
        )

        response = self.client.get(
            f"/workflows/{self.workflow.id}/tiles/step-2/delta-2/1,0.json"
        )
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(json.loads(response.content), {"error": "tile out of bounds"})

    def test_corrupt_cache_error(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", [1]))
        )
        delete_parquet_files_for_step(self.workflow.id, self.step2.id)

        response = self.client.get(
            f"/workflows/{self.workflow.id}/tiles/step-2/delta-2/0,0.json"
        )
        self.assertEqual(response.status_code, status.NOT_FOUND)
        self.assertEqual(
            json.loads(response.content),
            {"error": "result went away; please try again with another delta_id"},
        )

    def test_json(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )

        response = self.client.get(
            f"/workflows/{self.workflow.id}/tiles/step-2/delta-2/0,0.json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"rows": [["a"], ["b"]]})


class CurrentTableTest(StepViewTestCase):
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.step1 = self.tab.steps.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )
        self.step2 = self.tab.steps.create(
            order=1, slug="step-2", last_relevant_delta_id=2
        )

    def test_current_table_zero_columns(self):
        write_to_rendercache(self.workflow, self.step2, 2, make_table())

        # CSV
        response = self.client.get(
            f"/workflows/{self.workflow.id}/steps/step-2/current-result-table.csv"
        )
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(list(response.streaming_content), [])

        # JSON
        response = self.client.get(
            f"/workflows/{self.workflow.id}/steps/step-2/current-result-table.json"
        )
        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(read_streaming_json(response), [])

    def test_current_table_json(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )

        response = self.client.get(
            f"/workflows/{self.workflow.id}/steps/step-2/current-result-table.json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(read_streaming_json(response), [{"A": "a"}, {"A": "b"}])

    def test_deprecated_current_table_json(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )

        response = self.client.get(f"/public/moduledata/live/{self.step2.id}.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(read_streaming_json(response), [{"A": "a"}, {"A": "b"}])

    def test_current_table_csv(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )

        response = self.client.get(
            f"/workflows/{self.workflow.id}/steps/step-2/current-result-table.csv"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"A\na\nb")

    def test_deprecated_current_table_csv(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )

        response = self.client.get(f"/public/moduledata/live/{self.step2.id}.csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"A\na\nb")

    def test_secret_link(self):
        write_to_rendercache(
            self.workflow, self.step2, 2, make_table(make_column("A", ["a", "b"]))
        )
        self.workflow.secret_id = "wsecret"
        self.workflow.public = False
        self.workflow.save(update_fields=["public", "secret_id"])
        self.client.logout()
        # Regular link doesn't work...
        response = self.client.get(
            f"/workflows/{self.workflow.id}/steps/step-2/current-result-table.csv"
        )
        self.assertEqual(response.status_code, 403)

        # ... but secret link does!
        response = self.client.get(
            f"/workflows/wsecret/steps/step-2/current-result-table.csv"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"A\na\nb")
