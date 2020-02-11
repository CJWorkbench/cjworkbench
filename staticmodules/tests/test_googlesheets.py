import contextlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import io
import logging
from pathlib import Path
import unittest
import ssl
import threading
from typing import Any, ContextManager, Dict, Optional
import pandas as pd
import pyarrow
from staticmodules import googlesheets
from staticmodules.googlesheets import fetch_arrow, render_arrow, migrate_params
from .util import MockHttpResponse, MockParams
from cjwkernel.types import (
    ArrowTable,
    I18nMessage,
    FetchResult,
    RenderError,
    RenderResult,
)
from cjwkernel.tests.util import assert_arrow_table_equals, parquet_file
from cjwkernel.util import tempfile_context
from cjwmodule.http import httpfile

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


class FetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ssl_path = Path(__file__).parent / "test_data" / "ssl"

        cls.ssl_server_ctx = ssl.SSLContext()
        cls.ssl_server_ctx.load_cert_chain(
            ssl_path / "server-chain.crt", keyfile=ssl_path / "server.key"
        )

        cls.ssl_client_ctx = ssl.SSLContext()
        cls.ssl_client_ctx.load_verify_locations(ssl_path / "ca.crt")

    def setUp(self):
        super().setUp()
        self.last_http_requestline = None
        self.mock_http_response = None

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self2):
                self.last_http_requestline = self2.requestline
                r = self.mock_http_response
                if r is None:
                    raise RuntimeError("Tests must overwrite self.mock_http_response")

                self2.send_response_only(r.status_code)
                for header, value in r.headers:
                    self2.send_header(header, value)
                self2.end_headers()
                self2.wfile.write(r.body)

        self.server = HTTPServer(("localhost", 0), Handler)
        self.server.socket = self.ssl_server_ctx.wrap_socket(
            self.server.socket, server_side=True
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.005}
        )
        self.server_thread.setDaemon(True)
        self.server_thread.start()

        self.old_ssl_context = googlesheets.SSL_CONTEXT
        self.old_api_url = googlesheets.GDRIVE_API_URL
        googlesheets.GDRIVE_API_URL = (
            f"https://{self.server.server_address[0]}:{self.server.server_address[1]}"
        )
        googlesheets.SSL_CONTEXT = self.ssl_client_ctx

    def tearDown(self):
        self.server.shutdown()
        self.server_thread.join()
        googlesheets.GDRIVE_API_URL = self.old_api_url
        googlesheets.SSL_CONTEXT = self.old_ssl_context
        super().tearDown()

    @contextlib.contextmanager
    def fetch(
        self, params: Dict[str, Any], secrets: Dict[str, Any]
    ) -> ContextManager[FetchResult]:
        with tempfile_context(prefix="output-") as output_path:
            with self.assertLogs(level=logging.DEBUG) as cm:
                yield fetch_arrow(params, secrets, None, None, output_path)

    def test_fetch_nothing(self):
        with tempfile_context(prefix="output-") as output_path:
            result = fetch_arrow(P(file=None), {}, None, None, output_path)
            self.assertEqual(
                result.errors,
                [RenderError(I18nMessage.TODO_i18n("Please choose a file"))],
            )

    def test_fetch_native_sheet(self):
        body = b"A,B\nx,y\nz,a"
        self.mock_http_response = MockHttpResponse.ok(
            body, [("Content-Type", "text/csv")]
        )
        with self.fetch(P(), secrets(DEFAULT_SECRET)) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers, [("content-type", "text/csv"), ("content-length", "11")]
                )
        self.assertRegex(
            self.last_http_requestline, "/files/.*/export\?mimeType=text%2Fcsv"
        )

    def test_fetch_csv_file(self):
        body = b"A,B\nx,y\nz,a"
        self.mock_http_response = MockHttpResponse.ok(
            body, [("Content-Type", "text/csv")]
        )
        with self.fetch(
            P(file={**default_file, "mimeType": "text/csv"}), secrets(DEFAULT_SECRET)
        ) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers, [("content-type", "text/csv"), ("content-length", "11")]
                )
        self.assertRegex(self.last_http_requestline, "/files/.*?alt=media")

    def test_fetch_tsv_file(self):
        body = b"A\tB\nx\ty\nz\ta"
        self.mock_http_response = MockHttpResponse.ok(
            body, [("Content-Type", "text/tab-separated-values")]
        )
        with self.fetch(
            P(file={**default_file, "mimeType": "text/tab-separated-values"}),
            secrets(DEFAULT_SECRET),
        ) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers,
                    [
                        ("content-type", "text/tab-separated-values"),
                        ("content-length", "11"),
                    ],
                )
        self.assertRegex(self.last_http_requestline, "/files/.*?alt=media")

    def test_fetch_xls_file(self):
        body = b"abcd"
        self.mock_http_response = MockHttpResponse.ok(
            body, [("Content-Type", "application/vnd.ms-excel")]
        )
        with self.fetch(
            P(file={**default_file, "mimeType": "application/vnd.ms-excel"}),
            secrets(DEFAULT_SECRET),
        ) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers,
                    [
                        ("content-type", "application/vnd.ms-excel"),
                        ("content-length", "4"),
                    ],
                )
        self.assertRegex(self.last_http_requestline, "/files/.*?alt=media")

    def test_fetch_xlsx_file(self):
        body = b"abcd"
        self.mock_http_response = MockHttpResponse.ok(
            body,
            [
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            ],
        )
        with self.fetch(
            P(
                file={
                    **default_file,
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
            ),
            secrets(DEFAULT_SECRET),
        ) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers,
                    [
                        (
                            "content-type",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ),
                        ("content-length", "4"),
                    ],
                )
        self.assertRegex(self.last_http_requestline, "/files/.*?alt=media")

    def test_missing_secret_error(self):
        with tempfile_context() as output_path:
            result = fetch_arrow(P(), secrets(None), None, None, output_path)
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [RenderError(I18nMessage.TODO_i18n("Please connect to Google Drive."))],
            )
        # Should not make any request
        self.assertIsNone(self.last_http_requestline)

    def test_invalid_auth_error(self):
        self.mock_http_response = MockHttpResponse(401)
        with self.fetch(P(), secrets=secrets(DEFAULT_SECRET)) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage.TODO_i18n(
                            "Invalid credentials. Please reconnect to Google Drive."
                        )
                    )
                ],
            )

    def test_not_found(self):
        self.mock_http_response = MockHttpResponse(404)
        with self.fetch(P(), secrets=secrets(DEFAULT_SECRET)) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage.TODO_i18n(
                            "File not found. Please choose a different file."
                        )
                    )
                ],
            )

    def test_no_access_error(self):
        self.mock_http_response = MockHttpResponse(403)
        with self.fetch(P(), secrets=secrets(DEFAULT_SECRET)) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage.TODO_i18n(
                            "You chose a file your logged-in user cannot access. "
                            "Please reconnect to Google Drive or choose a different file."
                        )
                    )
                ],
            )

    def test_unhandled_http_error(self):
        # A response aiohttp can't handle
        self.mock_http_response = MockHttpResponse.ok(
            b"hi", headers=[("Content-Encoding", "gzip")]
        )
        with self.fetch(P(), secrets=secrets(DEFAULT_SECRET)) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        # googlesheet should pass through aiohttp's message
                        I18nMessage(
                            "http.errors.HttpErrorGeneric",
                            {"type": "DecodingError"},
                            "cjwmodule",
                        )
                    )
                ],
            )


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.ctx = contextlib.ExitStack()
        self.output_path = self.ctx.enter_context(tempfile_context(suffix="output-"))

    def tearDown(self):
        self.ctx.close()

    def test_render_no_file(self):
        result = render_arrow(ArrowTable(), P(), "tab-x", None, self.output_path)
        assert_arrow_table_equals(result.table, ArrowTable())
        self.assertEqual(result.errors, [])

    def test_render_fetch_error(self):
        errors = [RenderResult(I18nMessage("x", {"y": "z"}))]
        with tempfile_context() as empty_path:
            result = render_arrow(
                ArrowTable(),
                P(),
                "tab-x",
                FetchResult(empty_path, errors),
                self.output_path,
            )
        assert_arrow_table_equals(result.table, ArrowTable())
        self.assertEqual(result.errors, errors)

    def test_render_deprecated_parquet(self):
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            result = render_arrow(
                ArrowTable(), P(), "tab-x", FetchResult(fetched_path), self.output_path
            )
        assert_arrow_table_equals(result.table, {"A": [1, 2], "B": [3, 4]})
        self.assertEqual(result.errors, [])

    def test_render_deprecated_parquet_warning(self):
        errors = [RenderError(I18nMessage.TODO_i18n("truncated table"))]
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            result = render_arrow(
                ArrowTable(),
                P(),
                "tab-x",
                FetchResult(fetched_path, errors=errors),
                self.output_path,
            )
        assert_arrow_table_equals(result.table, {"A": [1, 2], "B": [3, 4]})
        self.assertEqual(result.errors, errors)

    def test_render_deprecated_parquet_has_header_false(self):
        # This behavior is totally awful, but we support it for backwards
        # compatibility.
        #
        # Back in the day, we parsed during fetch. But has_header can change
        # between fetch and render. We were lazy, so we made fetch() follow the
        # most-common path: has_header=True. Then, in render(), we would "undo"
        # the change if has_header=False. This was lossy. It took a lot of time
        # to figure it out. It was _never_ wise to code this. Now we need to
        # support these lossy, mangled files.
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            result = render_arrow(
                ArrowTable(),
                P(has_header=False),
                "tab-x",
                FetchResult(fetched_path),
                self.output_path,
            )
        assert_arrow_table_equals(
            result.table, {"0": ["A", "1", "2"], "1": ["B", "3", "4"]}
        )
        self.assertEqual(result.errors, [])

    def test_render_has_header_true(self):
        with tempfile_context("http") as http_path:
            httpfile.write(
                http_path,
                {"url": "https://blah"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"A,B\na,b"),
            )
            result = render_arrow(
                ArrowTable(),
                P(has_header=True),
                "tab-x",
                FetchResult(http_path),
                self.output_path,
            )
        assert_arrow_table_equals(result.table, {"A": ["a"], "B": ["b"]})
        self.assertEqual(result.errors, [])

    def test_render_has_header_false(self):
        with tempfile_context("http") as http_path:
            httpfile.write(
                http_path,
                {"url": "https://blah"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"1,2\n3,4"),
            )
            result = render_arrow(
                ArrowTable(),
                P(has_header=False),
                "tab-x",
                FetchResult(http_path),
                self.output_path,
            )
        assert_arrow_table_equals(
            result.table,
            {
                "Column 1": pyarrow.array([1, 3], pyarrow.int8()),
                "Column 2": pyarrow.array([2, 4], pyarrow.int8()),
            },
        )
        self.assertEqual(result.errors, [])

    def test_render_missing_fetch_result_returns_empty(self):
        result = render_arrow(ArrowTable(), P(), "tab-x", None, self.output_path)
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(result.errors, [])


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
