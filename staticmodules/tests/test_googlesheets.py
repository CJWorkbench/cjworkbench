import logging
from pathlib import Path
import unittest
from unittest.mock import patch
from typing import Any, Dict, Optional
import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import pandas as pd
from yarl import URL
from staticmodules.googlesheets import fetch, render, migrate_params
from .util import MockParams
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.tests.pandas.util import assert_process_result_equal

expected_table = pd.DataFrame({"foo": [1, 2], "bar": [2, 3]})

DEFAULT_SECRET = {
    "name": "x",
    "secret": {
        # As returned by fetcher.secrets.process_secret_oauth2()
        "token_type": "Bearer",
        "access_token": "an-access-token",
    },
}
default_file = {
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
    "url": "http://example.org/police-data",
    "mimeType": "application/vnd.google-apps.spreadsheet",
}


P = MockParams.factory(file=default_file, has_header=True)


def secrets(secret: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if secret:
        return {"google_credentials": secret}
    else:
        return {}


MOCK_ROUTES = {
    "csv": (
        "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
        "/drive/v3/files/aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj?alt=media",
        web.Response(body=b"foocsv,bar\n1,2\n2,3"),
        pd.DataFrame({"foocsv": [1, 2], "bar": [2, 3]}),
    ),
    "tsv": (),
    "xls": (),
    "xlsx": (),
}


class FetchTests(AioHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.export_path_responses = {}
        self.file_path_responses = {}

        self.logger = logging.getLogger("aiohttp.access")
        self.old_log_level = self.logger.level
        self.logger.setLevel(logging.WARN)

        self.client_patcher = patch.object(
            aiohttp, "ClientSession", lambda: self.client
        )
        self.client_patcher.start()

        self.last_request = None

        # googlesheets constructs absolute URLs, not just paths. That isn't what
        # AioHTTPTestCase normally expects.
        self.server.make_url = lambda path: self.server._root.join(URL(path).relative())

    def tearDown(self):
        self.client_patcher.stop()
        self.logger.setLevel(self.old_log_level)
        super().tearDown()

    async def export_handler(self, request: web.Request) -> web.Response:
        # raise KeyError (500 error)
        self.last_request = request
        self.assertEqual(
            self.last_request.headers["Authorization"], "Bearer an-access-token"
        )
        return self.export_path_responses[request.match_info["sheet_id"]]

    async def file_handler(self, request: web.Request) -> web.Response:
        # raise KeyError (500 error)
        self.last_request = request
        return self.file_path_responses[request.match_info["sheet_id"]]

    async def get_application(self):  # AioHTTPTestCase requirement
        app = web.Application()
        app.router.add_get("/drive/v3/files/{sheet_id}/export", self.export_handler)
        app.router.add_get("/drive/v3/files/{sheet_id}", self.file_handler)
        return app

    @unittest_run_loop
    async def test_fetch_native_sheet(self):
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(body=b"A,B\nx,y\nz,a")
        fetch_result = await fetch(P(), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(
            fetch_result, pd.DataFrame({"A": ["x", "z"], "B": ["y", "a"]})
        )

    @unittest_run_loop
    async def test_fetch_csv_file(self):
        self.file_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(body=b"A,B\nx,y\nz,a")
        fetch_result = await fetch(
            P(file={**default_file, "mimeType": "text/csv"}),
            secrets=secrets(DEFAULT_SECRET),
        )
        assert_process_result_equal(
            fetch_result, pd.DataFrame({"A": ["x", "z"], "B": ["y", "a"]})
        )

    @unittest_run_loop
    async def test_fetch_tsv_file(self):
        self.file_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(body=b"A\tB\nx\ty\nz\tb")
        fetch_result = await fetch(
            P(file={**default_file, "mimeType": "text/tab-separated-values"}),
            secrets=secrets(DEFAULT_SECRET),
        )
        assert_process_result_equal(
            fetch_result, pd.DataFrame({"A": ["x", "z"], "B": ["y", "b"]})
        )

    @unittest_run_loop
    async def test_fetch_xls_file(self):
        self.file_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.FileResponse(Path(__file__).parent / "test_data" / "example.xls")
        fetch_result = await fetch(
            P(file={**default_file, "mimeType": "application/vnd.ms-excel"}),
            secrets=secrets(DEFAULT_SECRET),
        )
        assert_process_result_equal(
            fetch_result, pd.DataFrame({"foo": [1, 2], "bar": [2, 3]})
        )

    @unittest_run_loop
    async def test_fetch_xlsx_file(self):
        self.file_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.FileResponse(Path(__file__).parent / "test_data" / "example.xls")
        fetch_result = await fetch(
            P(
                file={
                    **default_file,
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
            ),
            secrets=secrets(DEFAULT_SECRET),
        )
        assert_process_result_equal(
            fetch_result, pd.DataFrame({"foo": [1, 2], "bar": [2, 3]})
        )

    @unittest_run_loop
    async def test_missing_secret_error(self):
        fetch_result = await fetch(P(), secrets=secrets(None))
        # Should not make any request
        self.assertIsNone(self.last_request)
        assert_process_result_equal(fetch_result, "Please connect to Google Drive.")

    @unittest_run_loop
    async def test_invalid_auth_error(self):
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(status=401)
        fetch_result = await fetch(P(), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(
            fetch_result, "Invalid credentials. Please reconnect to Google Drive."
        )

    @unittest_run_loop
    async def test_not_found(self):
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(status=404)
        fetch_result = await fetch(P(), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(
            fetch_result, "File not found. Please choose a different file."
        )

    @unittest_run_loop
    async def test_no_access_error(self):
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(status=403)
        fetch_result = await fetch(P(), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(
            fetch_result,
            "You chose a file your logged-in user cannot access. Please reconnect to Google Drive or choose a different file.",
        )

    @unittest_run_loop
    async def test_unhandled_http_error(self):
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(body=b"hi", headers={"Content-Encoding": "gzip"})
        fetch_result = await fetch(P(), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(
            fetch_result,
            # googlesheet should pass through aiohttp's message
            "Error during GDrive request: 400, message='Can not decode content-encoding: gzip'",
        )

    @unittest_run_loop
    async def test_ignore_first_row_header(self):
        # Currently, we parse the table during fetch. For legacy reasons, we
        # parse with has_header_row=True, _and_ we auto-convert numbers. That
        # means during fetch, we may lose information -- e.g., we may convert
        # "3.5000" to 3.5 (losing the "000"); or we may convert "" to `null`
        # (indistinguishable from _actual_ null).
        #
        # For now, unit-test that this is indeed our behavior. render() relies
        # on it.
        #
        # TODO store _raw_ fetched data; make "first row is header" a parse
        # option used during render.
        self.export_path_responses[
            "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj"
        ] = web.Response(body=b"A,B\n1,2")
        fetch_result = await fetch(P(has_header=False), secrets=secrets(DEFAULT_SECRET))
        assert_process_result_equal(fetch_result, pd.DataFrame({"A": [1], "B": [2]}))


class RenderTests(unittest.TestCase):
    def test_render_no_file(self):
        result = render(pd.DataFrame(), P(), fetch_result=ProcessResult())
        assert_process_result_equal(result, None)

    def test_render_fetch_error(self):
        result = render(
            pd.DataFrame(), P(), fetch_result=ProcessResult(error="please log in")
        )
        assert_process_result_equal(result, "please log in")

    def test_render_fetch_warning(self):
        result = render(
            pd.DataFrame(), P(), fetch_result=ProcessResult(expected_table, "truncated")
        )
        assert_process_result_equal(result, (expected_table, "truncated"))

    def test_render_ok(self):
        result = render(pd.DataFrame(), P(), fetch_result=ProcessResult(expected_table))
        assert_process_result_equal(result, expected_table)

    def test_render_missing_fetch_result_returns_empty(self):
        result = render(pd.DataFrame(), P(), fetch_result=None)
        assert_process_result_equal(result, pd.DataFrame())

    def test_render_has_header_false(self):
        # TODO "no first row" should be a parse option. Fetch should store
        # raw data, and render should parse.
        result = render(
            pd.DataFrame(),
            P(has_header=False),
            fetch_result=ProcessResult(pd.DataFrame({"A": [1], "B": [2]})),
        )
        assert_process_result_equal(
            result, pd.DataFrame({"0": ["A", "1"], "1": ["B", "2"]})
        )


class MigrateParamsTest(unittest.TestCase):
    def test_v0_with_file(self):
        self.assertEqual(
            migrate_params(
                {
                    "has_header": False,
                    "version_select": "",
                    "googlefileselect": (
                        '{"id":"1AR-sdfsdf","name":"Filename","url":"https://docs.goo'
                        'gle.com/a/org/spreadsheets/d/1MJsdfwer/view?usp=drive_web","'
                        'mimeType":"text/csv"}'
                    ),
                }
            ),
            {
                "has_header": False,
                "version_select": "",
                "file": {
                    "id": "1AR-sdfsdf",
                    "name": "Filename",
                    "url": (
                        "https://docs.google.com/a/org/spreadsheets/"
                        "d/1MJsdfwer/view?usp=drive_web"
                    ),
                    "mimeType": "text/csv",
                },
            },
        )

    def test_v0_no_file(self):
        self.assertEqual(
            migrate_params(
                {"has_header": False, "version_select": "", "googlefileselect": ""}
            ),
            {"has_header": False, "version_select": "", "file": None},
        )

    def test_v1(self):
        self.assertEqual(
            migrate_params(
                {
                    "has_header": False,
                    "version_select": "",
                    "file": {
                        "id": "1AR-sdfsdf",
                        "name": "Filename",
                        "url": (
                            "https://docs.google.com/a/org/spreadsheets/"
                            "d/1MJsdfwer/view?usp=drive_web"
                        ),
                        "mimeType": "text/csv",
                    },
                }
            ),
            {
                "has_header": False,
                "version_select": "",
                "file": {
                    "id": "1AR-sdfsdf",
                    "name": "Filename",
                    "url": (
                        "https://docs.google.com/a/org/spreadsheets/"
                        "d/1MJsdfwer/view?usp=drive_web"
                    ),
                    "mimeType": "text/csv",
                },
            },
        )
