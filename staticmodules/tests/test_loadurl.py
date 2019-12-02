import gzip
import json
import logging
from pathlib import Path
import unittest
from unittest.mock import patch
import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import pandas as pd
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.util import tempfile_context
from cjwkernel.tests.pandas.util import assert_process_result_equal
from cjwkernel.types import FetchResult
from cjwstate.tests.utils import mock_xlsx_path
from staticmodules.loadurl import fetch, render
from .util import MockParams

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
P = MockParams.factory(url="", has_header=True)


class FetchTests(AioHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.requests = []  # requests received this test run
        self.responses = {}  # stubbed responses

        self.logger = logging.getLogger("aiohttp.access")
        self.old_log_level = self.logger.level
        self.logger.setLevel(logging.WARN)

        self.client_patcher = patch.object(
            aiohttp, "ClientSession", lambda: self.client.session
        )
        self.client_patcher.start()

    def tearDown(self):
        self.client_patcher.stop()
        self.logger.setLevel(self.old_log_level)
        super().tearDown()

    def build_url(self, path: str) -> str:
        """
        Build a URL that points to our HTTP server.
        """
        return str(self.server.make_url(path))

    async def handler(self, request: web.Request) -> web.Response:
        self.requests.append(request)
        response = self.responses[request.match_info["path"]]
        if callable(response):  # lambda supports repeated hits to same URL
            response = response()
        return response

    async def get_application(self):  # AioHTTPTestCase requirement
        app = web.Application()
        app.router.add_get("/{path:.*}", self.handler)
        return app

    def assertFetchedFile(
        self,
        actual: Path,
        expected_url,
        expected_status,
        expected_headers,
        expected_body,
    ):
        with actual.open("rb") as f:
            with gzip.GzipFile(fileobj=f, mode="rb") as zf:
                actual_params = json.loads(zf.readline()[:-2].decode("utf-8"))
                expected_params = {"url": expected_url}
                self.assertEqual(actual_params, expected_params, "URL mismatch")

                actual_status = zf.readline()[:-2].decode("ascii")
                self.assertEqual(actual_status, expected_status, "HTTP status mismatch")

                actual_headers = []
                while True:
                    line = zf.readline()[:-2].decode("latin1")
                    if not line:
                        break
                    actual_headers.append(line)
                self.assertEqual(
                    frozenset(actual_headers),
                    frozenset(expected_headers),
                    "HTTP header mismatch",
                )

                actual_body = zf.read()
                self.assertEqual(actual_body, expected_body, "HTTP body mismatch")

    @unittest_run_loop
    async def test_fetch_csv(self):
        self.responses["path/to.csv"] = web.Response(
            content_type="text/csv",
            charset="ISO-8859-1",
            headers={"Server": "test server"},
            body="A,B\n1,café".encode("latin1"),
        )
        with tempfile_context("output-") as output_path:
            url = self.build_url("/path/to.csv")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertFetchedFile(
                result,
                url,
                "200 OK",
                [
                    "Content-Type: text/csv; charset=ISO-8859-1",
                    "Server: test server",
                    "Cjw-Original-Content-Length: 10",
                ],
                "A,B\n1,café".encode("latin1"),
            )

    @unittest_run_loop
    async def test_fetch_gzip_encoded_csv(self):
        response = web.Response(
            content_type="text/csv",
            charset="ISO-8859-1",
            headers={"Server": "test server"},
            body="A,B\n1,café\n1,café\n1,café".encode("latin1"),
        )
        response.enable_compression(web.ContentCoding.gzip)
        self.responses["path/to.csv.gz"] = response
        with tempfile_context("output-") as output_path:
            url = self.build_url("/path/to.csv.gz")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertFetchedFile(
                result,
                url,
                "200 OK",
                [
                    "Content-Type: text/csv; charset=ISO-8859-1",
                    "Server: test server",
                    "Cjw-Original-Content-Encoding: gzip",
                    "Cjw-Original-Content-Length: 32",
                ],
                "A,B\n1,café\n1,café\n1,café".encode("latin1"),
            )

    @unittest_run_loop
    async def test_fetch_deflate_encoded_csv(self):
        response = web.Response(
            content_type="text/csv",
            charset="ISO-8859-1",
            headers={"Server": "test server"},
            body="A,B\n1,café\n1,café\n1,café".encode("latin1"),
        )
        response.enable_compression(web.ContentCoding.deflate)
        self.responses["path/to.csv.gz"] = response
        with tempfile_context("output-") as output_path:
            url = self.build_url("/path/to.csv.gz")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertFetchedFile(
                result,
                url,
                "200 OK",
                [
                    "Content-Type: text/csv; charset=ISO-8859-1",
                    "Server: test server",
                    "Cjw-Original-Content-Encoding: deflate",
                    "Cjw-Original-Content-Length: 14",
                ],
                "A,B\n1,café\n1,café\n1,café".encode("latin1"),
            )

    @unittest_run_loop
    async def test_fetch_chunked_csv(self):
        response = web.Response(
            content_type="text/csv",
            charset="ISO-8859-1",
            headers={"Server": "test server"},
            body="A,B\n1,café".encode("latin1"),
        )
        response.enable_chunked_encoding()
        self.responses["path/to.csv.chunks"] = response
        with tempfile_context("output-") as output_path:
            url = self.build_url("/path/to.csv.chunks")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertEqual(result, output_path)
            self.assertFetchedFile(
                result,
                url,
                "200 OK",
                [
                    "Content-Type: text/csv; charset=ISO-8859-1",
                    "Server: test server",
                    "Cjw-Original-Transfer-Encoding: chunked",
                ],
                "A,B\n1,café".encode("latin1"),
            )

    @unittest_run_loop
    async def test_fetch_http_404(self):
        self.responses["bad-url"] = web.HTTPNotFound()
        with tempfile_context("output-") as output_path:
            url = self.build_url("/bad-url")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertEqual(result, "Error from server: 404 Not Found")
            self.assertEqual(output_path.read_bytes(), b"")

    @unittest_run_loop
    async def test_fetch_invalid_url(self):
        with tempfile_context("output-") as output_path:
            result = await fetch(P(url="not-a-\\éURL"), output_path=output_path)
            self.assertEqual(result, "Invalid URL")
            self.assertEqual(output_path.read_bytes(), b"")

    @unittest_run_loop
    async def test_fetch_follow_redirect(self):
        self.responses["url1.csv"] = web.HTTPFound(self.build_url("/url2.csv"))
        self.responses["url2.csv"] = web.HTTPFound(self.build_url("/url3.csv"))
        self.responses["url3.csv"] = web.Response(
            content_type="text/csv",
            charset="ISO-8859-1",
            headers={"Server": "test server"},
            body="A,B\n1,café".encode("latin1"),
        )
        with tempfile_context("output-") as output_path:
            url = self.build_url("/url1.csv")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertFetchedFile(
                result,
                url,
                "200 OK",
                [
                    "Content-Type: text/csv; charset=ISO-8859-1",
                    "Server: test server",
                    "Cjw-Original-Content-Length: 10",
                ],
                "A,B\n1,café".encode("latin1"),
            )

    @unittest_run_loop
    async def test_redirect_loop(self):
        url1 = self.build_url("/url1.csv")
        url2 = self.build_url("/url2.csv")
        # Make responses lambda functions, so server can return many copies
        self.responses["url1.csv"] = lambda: web.HTTPFound(url2)
        self.responses["url2.csv"] = lambda: web.HTTPFound(url1)
        with tempfile_context("output-") as output_path:
            url = self.build_url("/url1.csv")
            result = await fetch(P(url=url), output_path=output_path)
            self.assertEqual(
                result,
                "The server redirected us too many times. Please try a different URL.",
            )


class RenderTests(unittest.TestCase):
    def test_render_deprecated_process_result(self):
        result = render(
            pd.DataFrame(),
            P(has_header=True),
            fetch_result=ProcessResult(pd.DataFrame({"A": [1, 2]})),
        )
        assert_process_result_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_deprecated_process_result_and_has_header_false(self):
        # The deprecated loadurl load original data; so this is lossy.
        # Here we're testing the "happy path" where we miraculously switched
        # from text => number => text and formatting remained intact.
        result = render(
            pd.DataFrame(),
            P(has_header=False),
            fetch_result=ProcessResult(pd.DataFrame({"A": [1, 2]})),
        )
        # Deprecated: columns are numbered
        assert_process_result_equal(result, pd.DataFrame({"0": ["A", "1", "2"]}))

    def test_render_error_process_result(self):
        result = render(pd.DataFrame(), P(), fetch_result=ProcessResult.coerce("hi"))
        assert_process_result_equal(result, "hi")

    def test_render_empty_process_result(self):
        result = render(
            pd.DataFrame(), P(has_header=False), fetch_result=ProcessResult()
        )
        assert_process_result_equal(result, pd.DataFrame())

    def test_render_csv(self):
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.org/x"}',
                            b"200 OK",
                            b"Content-Type: text/csv; charset=utf-8",
                            b"",
                            b'A,B\n0,"y,z"\n1,2',
                        ]
                    )
                )
            )
            result = render(
                pd.DataFrame(), P(has_header=True), fetch_result=FetchResult(tf)
            )
            assert_process_result_equal(
                result, pd.DataFrame({"A": [0, 1], "B": ["y,z", "2"]})
            )

    def test_render_csv_header_false(self):
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.org/x"}',
                            b"200 OK",
                            b"Content-Type: text/csv; charset=utf-8",
                            b"",
                            b'A,B\n0,"y,z"\n1,2',
                        ]
                    )
                )
            )
            result = render(
                pd.DataFrame(), P(has_header=False), fetch_result=FetchResult(tf)
            )
            assert_process_result_equal(
                result,
                pd.DataFrame(
                    {"Column 1": ["A", "0", "1"], "Column 2": ["B", "y,z", "2"]}
                ),
            )

    def test_render_csv_use_ext_given_bad_content_type(self):
        # Use text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://raw.githubusercontent.com/user/project/x.csv"}',
                            b"200 OK",
                            b"Content-Type: text/plain",
                            b"",
                            b"A\n1\n2",
                        ]
                    )
                )
            )
            result = render(
                pd.DataFrame(), P(has_header=True), fetch_result=FetchResult(tf)
            )
            assert_process_result_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_csv_handle_nonstandard_mime_type(self):
        # Transform 'application/csv' into 'text/csv', etc.
        #
        # Sysadmins sometimes invent MIME types. We hard-code to rewrite fake
        # MIME types we've seen in the wild that seem unambiguous.
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.com/the.data?format=csv&foo=bar"}',
                            b"200 OK",
                            b"Content-Type: application/x-csv",
                            b"",
                            b"A\n1\n2",
                        ]
                    )
                )
            )
            result = render(
                pd.DataFrame(), P(has_header=True), fetch_result=FetchResult(tf)
            )
            assert_process_result_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_json(self):
        # Transform 'application/csv' into 'text/csv', etc.
        #
        # Sysadmins sometimes invent MIME types. We hard-code to rewrite fake
        # MIME types we've seen in the wild that seem unambiguous.
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.com/api/foo"}',
                            b"200 OK",
                            b"Content-Type: application/json",
                            b"",
                            b'[{"A":1},{"A": 2}]',
                        ]
                    )
                )
            )
            result = render(
                pd.DataFrame(),
                # has_header is ignored
                P(has_header=False),
                fetch_result=FetchResult(tf),
            )
            assert_process_result_equal(result, pd.DataFrame({"A": [1, 2]}))

    def test_render_json_invalid_json(self):
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.com/x.json"}',
                            b"200 OK",
                            b"Content-Type: application/json",
                            b"",
                            b"not json",
                        ]
                    )
                )
            )
            result = render(pd.DataFrame(), P(), fetch_result=FetchResult(tf))
            assert_process_result_equal(
                result, "JSON lexical error: invalid string in json text."
            )

    def test_render_xlsx(self):
        with open(mock_xlsx_path, "rb") as f:
            xlsx_bytes = f.read()
            xlsx_table = pd.read_excel(mock_xlsx_path)

        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.org/xlsx"}',
                            b"200 OK",
                            b"Content-Type: " + XLSX_MIME_TYPE.encode("latin1"),
                            b"",
                            xlsx_bytes,
                        ]
                    )
                )
            )
            result = render(pd.DataFrame(), P(), fetch_result=FetchResult(tf))
            assert_process_result_equal(result, xlsx_table)

    def test_render_xlsx_bad_content(self):
        with tempfile_context("fetch-") as tf:
            tf.write_bytes(
                gzip.compress(
                    b"\r\n".join(
                        [
                            b'{"url":"http://example.org/bad-xlsx"}',
                            b"200 OK",
                            b"Content-Type: " + XLSX_MIME_TYPE.encode("latin1"),
                            b"",
                            "ceçi n'est pas une .xlsx".encode("utf-8"),
                        ]
                    )
                )
            )
            result = render(pd.DataFrame(), P(), fetch_result=FetchResult(tf))
            assert_process_result_equal(
                result,
                (
                    "Error reading Excel file: Unsupported format, or corrupt "
                    'file: Expected BOF record; found b"ce\\xc3\\xa7i n\'"'
                ),
            )
