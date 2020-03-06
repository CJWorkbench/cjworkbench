import contextlib
import gzip
from http.server import HTTPServer, BaseHTTPRequestHandler
import io
import itertools
from pathlib import Path
import threading
from typing import ContextManager
import unittest
import zlib
import pyarrow
from cjwkernel.util import tempfile_context
from cjwkernel.tests.util import assert_arrow_table_equals, parquet_file
from cjwkernel.types import (
    ArrowTable,
    FetchResult,
    I18nMessage,
    RenderError,
    RenderResult,
)
from cjwmodule.http import httpfile
from staticmodules.loadurl import fetch, render
from .util import MockHttpResponse, MockParams

TestDataPath = Path(__file__).parent / "test_data"

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
P = MockParams.factory(url="", has_header=True)


class FetchTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.http_requestlines = []
        self.mock_http_response = None

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self2):
                self.http_requestlines.append(self2.requestline)
                r = self.mock_http_response
                if hasattr(r, "__next__"):
                    r = next(r)
                if r is None:
                    raise RuntimeError("Tests must overwrite self.mock_http_response")

                self2.send_response_only(r.status_code)
                for header, value in r.headers:
                    self2.send_header(header, value)
                self2.end_headers()
                write = self2.wfile.write
                if isinstance(r.body, list):
                    # chunked encoding
                    for chunk in r.body:
                        write(("%x\r\n" % len(chunk)).encode("ascii"))
                        write(chunk)
                        write(b"\r\n")
                    write(b"0\r\n\r\n")
                else:
                    # just write the bytes
                    write(r.body)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.005}
        )
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server_thread.join()
        super().tearDown()

    @contextlib.contextmanager
    def fetch(
        self, url: str = "", has_header: bool = True
    ) -> ContextManager[FetchResult]:
        with tempfile_context(prefix="output-") as output_path:
            errors = fetch(
                {"url": url, "has_header": has_header}, output_path=output_path
            )
            yield FetchResult(
                output_path, [RenderError(I18nMessage(*e)) for e in errors]
            )

    def build_url(self, path: str) -> str:
        """
        Build a URL that points to our HTTP server.
        """
        return "http://%s:%d%s" % (*self.server.server_address, path)

    def test_fetch_csv(self):
        body = b"A,B\nx,y\nz,a"
        url = self.build_url("/path/to.csv")
        self.mock_http_response = MockHttpResponse.ok(
            body, [("Content-Type", "text/csv; charset=utf-8")]
        )
        with self.fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)
                self.assertEqual(
                    headers,
                    [
                        ("content-type", "text/csv; charset=utf-8"),
                        ("content-length", "11"),
                    ],
                )

    def test_fetch_gzip_encoded_csv(self):
        body = b"A,B\nx,y\nz,a"
        url = self.build_url("/path/to.csv.gz")
        self.mock_http_response = MockHttpResponse.ok(
            gzip.compress(body),
            [("Content-Type", "text/csv; charset=utf-8"), ("Content-Encoding", "gzip")],
        )
        with self.fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)

    def test_fetch_deflate_encoded_csv(self):
        body = b"A,B\nx,y\nz,a"
        zo = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        zbody = zo.compress(body) + zo.flush()
        url = self.build_url("/path/to.csv.gz")
        self.mock_http_response = MockHttpResponse.ok(
            zbody,
            [
                ("Content-Type", "text/csv; charset=utf-8"),
                ("Content-Encoding", "deflate"),
            ],
        )
        with self.fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)

    def test_fetch_chunked_csv(self):
        self.mock_http_response = MockHttpResponse.ok(
            [b"A,B\nx", b",y\nz,", b"a"], [("Content-Type", "text/csv; charset=utf-8")]
        )
        url = self.build_url("/path/to.csv.chunks")
        with self.fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), b"A,B\nx,y\nz,a")

    def test_fetch_http_404(self):
        self.mock_http_response = MockHttpResponse(404, [("Content-Length", 0)])
        url = self.build_url("/not-found")
        with self.fetch(url) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage(
                            "http.errors.HttpErrorNotSuccess",
                            {"status_code": 404, "reason": "Not Found"},
                            "cjwmodule",
                        )
                    )
                ],
            )

    def test_fetch_invalid_url(self):
        with self.fetch("htt://blah") as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage("http.errors.HttpErrorInvalidUrl", {}, "cjwmodule")
                    )
                ],
            )

    def test_fetch_follow_redirect(self):
        url1 = self.build_url("/url1.csv")
        url2 = self.build_url("/url2.csv")
        url3 = self.build_url("/url3.csv")
        self.mock_http_response = iter(
            [
                MockHttpResponse(302, [("Location", url2)]),
                MockHttpResponse(302, [("Location", url3)]),
                MockHttpResponse.ok(b"A,B\n1,2", [("Content-Type", "text/csv")]),
            ]
        )
        with self.fetch(url1) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (parameters, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), b"A,B\n1,2")
                self.assertEqual(parameters, {"url": url1})
        self.assertIn("/url1.csv", self.http_requestlines[0])
        self.assertIn("/url2.csv", self.http_requestlines[1])
        self.assertIn("/url3.csv", self.http_requestlines[2])

    def test_redirect_loop(self):
        url1 = self.build_url("/url1.csv")
        url2 = self.build_url("/url2.csv")
        self.mock_http_response = itertools.cycle(
            [
                MockHttpResponse(302, [("Location", url2)]),
                MockHttpResponse(302, [("Location", url1)]),
            ]
        )
        with self.fetch(url1) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        I18nMessage(
                            "http.errors.HttpErrorTooManyRedirects", {}, "cjwmodule"
                        )
                    )
                ],
            )


class RenderTests(unittest.TestCase):
    @contextlib.contextmanager
    def render(self, params, fetch_result):
        with tempfile_context(prefix="output-", suffix=".arrow") as output_path:
            errors = render(
                ArrowTable(), params, output_path, fetch_result=fetch_result
            )
            table = ArrowTable.from_arrow_file_with_inferred_metadata(output_path)
            yield RenderResult(table, [RenderError(I18nMessage(*e)) for e in errors])

    def test_render_no_file(self):
        with self.render(P(), None) as result:
            assert_arrow_table_equals(result.table, ArrowTable())
            self.assertEqual(result.errors, [])

    def test_render_fetch_error(self):
        fetch_errors = [RenderError(I18nMessage("x", {"y": "z"}))]
        with tempfile_context() as empty_path:
            with self.render(P(), FetchResult(empty_path, fetch_errors)) as result:
                assert_arrow_table_equals(result.table, ArrowTable())
                self.assertEqual(result.errors, fetch_errors)

    def test_render_deprecated_parquet(self):
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            with self.render(P(), FetchResult(fetched_path)) as result:
                assert_arrow_table_equals(result.table, {"A": [1, 2], "B": [3, 4]})
                self.assertEqual(result.errors, [])

    def test_render_deprecated_parquet_warning(self):
        fetch_errors = [RenderError(I18nMessage.TODO_i18n("truncated table"))]
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            with self.render(P(), FetchResult(fetched_path, fetch_errors)) as result:
                assert_arrow_table_equals(result.table, {"A": [1, 2], "B": [3, 4]})
                self.assertEqual(result.errors, fetch_errors)

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
            with self.render(P(has_header=False), FetchResult(fetched_path)) as result:
                assert_arrow_table_equals(result.table, {"A": [1, 2], "B": [3, 4]})
                self.assertEqual(
                    result.errors,
                    [
                        RenderError(
                            I18nMessage.TODO_i18n(
                                "Please re-download this file to disable header-row handling"
                            )
                        )
                    ],
                )

    def test_render_has_header_true(self):
        with tempfile_context("http") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"A,B\na,b"),
            )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                assert_arrow_table_equals(result.table, {"A": ["a"], "B": ["b"]})
                self.assertEqual(result.errors, [])

    def test_render_has_header_false(self):
        with tempfile_context("http") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"1,2\n3,4"),
            )
            with self.render(P(has_header=False), FetchResult(http_path)) as result:
                assert_arrow_table_equals(
                    result.table,
                    {
                        "Column 1": pyarrow.array([1, 3], pyarrow.int8()),
                        "Column 2": pyarrow.array([2, 4], pyarrow.int8()),
                    },
                )
                self.assertEqual(result.errors, [])

    def test_render_csv_use_url_ext_given_bad_content_type(self):
        # Use text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/file.csv"},
                "200 OK",
                [("content-type", "text/plain")],
                # bytes will prove we used "csv" explicitly -- we didn't
                # take "text/plain" and decide to use a CSV sniffer to
                # find the delimiter.
                io.BytesIO(b"A;B\na;b"),
            )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                assert_arrow_table_equals(result.table, {"A;B": ["a;b"]})
                self.assertEqual(result.errors, [])

    def test_render_text_plain(self):
        # guess_mime_type_or_none() treats text/plain specially.
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/file.unknownext"},
                "200 OK",
                [("content-type", "text/plain")],
                io.BytesIO(b"A;B\na;b"),
            )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                self.assertEqual(result.errors, [])
                assert_arrow_table_equals(result.table, {"A": ["a"], "B": ["b"]})

    def test_render_csv_handle_nonstandard_mime_type(self):
        # Transform 'application/csv' into 'text/csv', etc.
        #
        # Sysadmins sometimes invent MIME types. We hard-code to rewrite fake
        # MIME types we've seen in the wild that seem unambiguous.
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "application/x-csv")],
                io.BytesIO(b"A,B\na,b"),
            )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                assert_arrow_table_equals(result.table, {"A": ["a"], "B": ["b"]})
                self.assertEqual(result.errors, [])

    def test_render_json(self):
        with tempfile_context("fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "application/json")],
                io.BytesIO(b'[{"A": "a"}]'),
            )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                self.assertEqual(result.errors, [])
                assert_arrow_table_equals(result.table, {"A": ["a"]})

    def test_render_xlsx(self):
        with tempfile_context("fetch-") as http_path:
            with (TestDataPath / "example.xlsx").open("rb") as xlsx_f:
                httpfile.write(
                    http_path,
                    {"url": "http://example.com/hello"},
                    "200 OK",
                    [("content-type", XLSX_MIME_TYPE)],
                    xlsx_f,
                )
            with self.render(P(has_header=True), FetchResult(http_path)) as result:
                self.assertEqual(result.errors, [])
                assert_arrow_table_equals(
                    result.table, {"foo": [1.0, 2.0], "bar": [2.0, 3.0]}
                )

    def test_render_xlsx_bad_content(self):
        with tempfile_context("fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", XLSX_MIME_TYPE)],
                io.BytesIO("ceçi n'est pas une .xlsx".encode("utf-8")),
            )
            with self.render(P(), FetchResult(http_path)) as result:
                self.assertEqual(
                    result,
                    RenderResult(
                        ArrowTable(),
                        [
                            RenderError(
                                I18nMessage.TODO_i18n(
                                    "Invalid XLSX file: xlnt::exception : failed to find zip header"
                                )
                            )
                        ],
                    ),
                )
