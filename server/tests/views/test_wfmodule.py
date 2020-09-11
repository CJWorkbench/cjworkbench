from collections import namedtuple
from datetime import datetime as dt
import json
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import override_settings
import pyarrow as pa
from rest_framework.test import APIRequestFactory
from rest_framework import status
from rest_framework.test import force_authenticate
from cjwkernel.types import Column, ColumnType, RenderResult
from cjwkernel.tests.util import arrow_table
from cjwstate import commands
from cjwstate.rendercache.io import (
    cache_render_result,
    delete_parquet_files_for_wf_module,
)
from cjwstate.models import Workflow
from cjwstate.tests.utils import LoggedInTestCase


FakeSession = namedtuple("FakeSession", ["session_key"])
FakeCachedRenderResult = namedtuple("FakeCachedRenderResult", ["result"])


async def async_noop(*args, **kwargs):
    pass


empty_data_json = {"start_row": 0, "end_row": 0, "rows": []}


@patch.object(commands, "queue_render", async_noop)
@patch.object(commands, "websockets_notify", async_noop)
class WfModuleTests(LoggedInTestCase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name="test", owner=self.user)
        self.tab = self.workflow.tabs.create(position=0)
        self.wf_module1 = self.tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=1
        )
        self.wf_module2 = self.tab.wf_modules.create(
            order=1, slug="step-2", last_relevant_delta_id=2
        )

        self.log_patcher = patch("server.utils.log_user_event_from_request")
        self.log_patch = self.log_patcher.start()
        self.factory = APIRequestFactory()

    def tearDown(self):
        self.log_patcher.stop()
        super().tearDown()

    def _augment_request(self, request, user: User, session_key: str) -> None:
        if user:
            force_authenticate(request, user=user)
        request.session = FakeSession(session_key)

    def _build_patch(
        self, *args, user: User = None, session_key: str = "a-key", **kwargs
    ):
        request = self.factory.patch(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    def _build_put(
        self, *args, user: User = None, session_key: str = "a-key", **kwargs
    ):
        request = self.factory.put(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    # Test some json conversion gotchas we encountered during development
    def test_pandas_13258(self):
        # simple test case where Pandas produces int64 column type, and json
        # conversion throws ValueError
        # https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257
        int64 = 2 ** 62 + 10
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [1, int64]})),
        )
        self.wf_module2.save()

        response = self.client.get("/api/wfmodules/%d/render" % self.wf_module2.id)
        self.assertEqual(response.status_code, 200)

    @override_settings(MAX_COLUMNS_PER_CLIENT_REQUEST=2)
    def test_max_columns_returned(self):
        # Only at most MAX_COLUMNS_PER_CLIENT_REQUEST should be returned,
        # since we do not display more than that. (This is a funky hack that
        # assumes the client will behave differently when it has >MAX columns.)
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [1], "B": [2], "C": [3], "D": [4]})),
        )

        response = self.client.get("/api/wfmodules/%d/render" % self.wf_module2.id)
        self.assertEqual(response.status_code, 200)
        # One column more than configured limit, so client knows to display
        # "too many columns".
        self.assertEqual(len(json.loads(response.content)["rows"][0]), 3)

    def test_wf_module_render(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(
                arrow_table(
                    {
                        "Class": ["math", "english", "history", "economics"],
                        "M": [10, None, 11, 20],
                        "F": [12, 7, 13, 20],
                    }
                )
            ),
        )

        response = self.client.get("/api/wfmodules/%d/render" % self.wf_module2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {
                "start_row": 0,
                "end_row": 4,
                "rows": [
                    {"Class": "math", "F": 12, "M": 10.0},
                    {"Class": "english", "F": 7, "M": None},
                    {"Class": "history", "F": 13, "M": 11.0},
                    {"Class": "economics", "F": 20, "M": 20.0},
                ],
            },
        )

    def test_wf_module_render_null_datetime(self):
        # Ran into problems 2019-09-06, when switching to Arrow
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(
                arrow_table(
                    {
                        "A": pa.array(
                            [dt(2019, 1, 2, 3, 4, 5, 6007, None), None],
                            pa.timestamp("ns"),
                        )
                    }
                )
            ),
        )

        response = self.client.get("/api/wfmodules/%d/render" % self.wf_module2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content)["rows"],
            [{"A": "2019-01-02T03:04:05.006007Z"}, {"A": None}],
        )

    def test_wf_module_render_missing_parquet_file(self):
        # https://www.pivotaltracker.com/story/show/161988744
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [1]})),
        )

        # Simulate a race: we're overwriting the cache or deleting the WfModule
        # or some-such.
        delete_parquet_files_for_wf_module(self.workflow.id, self.wf_module2.id)

        response = self.client.get("/api/wfmodules/%d/render" % self.wf_module2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content), {"end_row": 0, "rows": [], "start_row": 0}
        )

    def test_wf_module_render_only_rows(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [0, 1, 2, 3, 4]})),
        )

        response = self.client.get(
            "/api/wfmodules/%d/render?startrow=1&endrow=3" % self.wf_module2.id
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)
        body = json.loads(response.content)
        self.assertEqual(body["rows"], [{"A": 1}, {"A": 2}])
        self.assertEqual(body["start_row"], 1)
        self.assertEqual(body["end_row"], 3)

    def test_wf_module_render_clip_out_of_bounds(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [0, 1]})),
        )

        # index out of bounds should clip
        response = self.client.get(
            "/api/wfmodules/%d/render?startrow=-1&endrow=500" % self.wf_module2.id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {"start_row": 0, "end_row": 2, "rows": [{"A": 0}, {"A": 1}]},
        )

    def test_wf_module_render_start_row_after_end_row(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": [0, 1, 2, 3, 4]})),
        )

        response = self.client.get(
            "/api/wfmodules/%d/render?startrow=3&endrow=1" % self.wf_module2.id
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)
        body = json.loads(response.content)
        self.assertEqual(body["rows"], [])
        self.assertEqual(body["start_row"], 3)
        self.assertEqual(body["end_row"], 3)

    def test_wf_module_render_invalid_endrow(self):
        # index not a number -> bad request
        response = self.client.get(
            "/api/wfmodules/%d/render?startrow=0&endrow=frog" % self.wf_module2.id
        )
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_value_counts_str(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": ["a", "b", "b", "a", "c", None]})),
        )

        response = self.client.get(
            f"/api/wfmodules/{self.wf_module2.id}/value-counts?column=A"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content), {"values": {"a": 2, "b": 2, "c": 1}}
        )

    def test_value_counts_dictionary(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(
                arrow_table(
                    {"A": pa.array(["a", "b", "b", "a", "c", None]).dictionary_encode()}
                )
            ),
        )

        response = self.client.get(
            f"/api/wfmodules/{self.wf_module2.id}/value-counts?column=A"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content), {"values": {"a": 2, "b": 2, "c": 1}}
        )

    def test_value_counts_corrupt_cache(self):
        # https://www.pivotaltracker.com/story/show/161988744
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": ["a"]})),
        )
        # Simulate a race: we're overwriting the cache or deleting the WfModule
        # or some-such.
        delete_parquet_files_for_wf_module(self.workflow.id, self.wf_module2.id)

        response = self.client.get(
            f"/api/wfmodules/{self.wf_module2.id}/value-counts?column=A"
        )

        # We _could_ return an empty result set; but our only goal here is
        # "don't crash" and this 404 seems to be the simplest implementation.
        # (We assume that if the data is deleted, the user has moved elsewhere
        # and this response is going to be ignored.)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": 'column "A" not found'}
        )

    def test_value_counts_disallow_non_text(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(
                arrow_table(
                    {"A": [1, 2, 3, 2, 1]},
                    columns=[Column("A", ColumnType.Number(format="{:.2f}"))],
                )
            ),
        )

        response = self.client.get(
            f"/api/wfmodules/{self.wf_module2.id}/value-counts?column=A"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), {"values": {}})

    def test_value_counts_param_invalid(self):
        response = self.client.get(f"/api/wfmodules/{self.wf_module2.id}/value-counts")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content), {"error": 'Missing a "column" parameter'}
        )

    def test_value_counts_missing_column(self):
        cache_render_result(
            self.workflow,
            self.wf_module2,
            self.wf_module2.last_relevant_delta_id,
            RenderResult(arrow_table({"A": ["a", "b"]})),
        )

        response = self.client.get(
            f"/api/wfmodules/{self.wf_module2.id}/value-counts?column=B"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            json.loads(response.content), {"error": 'column "B" not found'}
        )
