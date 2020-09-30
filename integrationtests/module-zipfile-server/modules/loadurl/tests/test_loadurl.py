from __future__ import annotations

import contextlib
import gzip
import io
import itertools
import tempfile
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ContextManager, List, NamedTuple, Optional, Tuple, Union

import cjwparquet
import pyarrow
from cjwmodule.http import httpfile
from cjwmodule.i18n import I18nMessage
from cjwmodule.testing.i18n import cjwmodule_i18n_message, i18n_message

from .. import loadurl

TestDataPath = Path(__file__).parent / "files"

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class RenderError(NamedTuple):
    message: I18nMessage


class FetchResult(NamedTuple):
    path: Optional[Path] = None
    errors: List[RenderError] = []


class RenderResult(NamedTuple):
    table: Optional[pyarrow.Table]
    errors: List[I18nMessage] = []


class MockHttpResponse(NamedTuple):
    status_code: int = 200
    """HTTP status code"""

    headers: List[Tuple[str, str]] = []
    """List of headers -- including Content-Length, Transfer-Encoding, etc."""

    body: Union[bytes, List[bytes]] = b""
    """
    HTTP response body.

    If this is `bytes` (including the default, `b""`), then `headers` requires
    a `Content-Length`. If this is a `List[bytes]`, then `headers` requires
    `Transfer-Encoding: chunked`.
    """

    @classmethod
    def ok(
        cls, body: bytes = b"", headers: List[Tuple[str, str]] = []
    ) -> MockHttpResponse:
        if isinstance(body, bytes):
            if not any(h[0].upper() == "CONTENT-LENGTH" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("Content-Length", str(len(body)))]
        elif isinstance(body, list):
            if not any(h[0].upper() == "TRANSFER-ENCODING" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("Transfer-Encoding", "chunked")]
        else:
            raise TypeError("body must be bytes or List[bytes]; got %r" % type(body))
        return cls(status_code=200, body=body, headers=headers)


def P(**kwargs):
    return {"url": "", "has_header": True, **kwargs}


@contextlib.contextmanager
def tempfile_context(**kwargs):
    with tempfile.NamedTemporaryFile(**kwargs) as tf:
        yield Path(tf.name)


@contextlib.contextmanager
def parquet_file(d):
    arrow_table = pyarrow.table(d)
    with tempfile.NamedTemporaryFile(suffix=".parquet") as tf:
        path = Path(tf.name)
        cjwparquet.write(path, arrow_table)
        yield path


def assert_arrow_table_equals(actual, expected):
    if actual is None or expected is None:
        assert (actual is None) == (expected is None)
    else:
        if isinstance(expected, dict):
            expected = pyarrow.table(expected)
        assert actual.column_names == expected.column_names
        assert [c.type for c in actual.columns] == [c.type for c in expected.columns]
        assert actual.to_pydict() == expected.to_pydict()


@contextlib.contextmanager
def call_fetch(url: str = "", has_header: bool = True) -> ContextManager[FetchResult]:
    with tempfile_context(prefix="output-") as output_path:
        errors = loadurl.fetch(
            {"url": url, "has_header": has_header}, output_path=output_path
        )
        yield FetchResult(output_path, [RenderError(e) for e in errors])


def call_render(params, fetch_result, **kwargs):
    with tempfile_context(suffix=".arrow") as output_path:
        errors = loadurl.render(
            None, params, output_path=output_path, fetch_result=fetch_result, **kwargs
        )
        if output_path.stat().st_size == 0:
            return None, errors
        else:
            with pyarrow.ipc.open_file(output_path) as reader:
                table = reader.read_all()
                return table, errors


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
        with call_fetch(url) as result:
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
        with call_fetch(url) as result:
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
        with call_fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), body)

    def test_fetch_chunked_csv(self):
        self.mock_http_response = MockHttpResponse.ok(
            [b"A,B\nx", b",y\nz,", b"a"], [("Content-Type", "text/csv; charset=utf-8")]
        )
        url = self.build_url("/path/to.csv.chunks")
        with call_fetch(url) as result:
            self.assertEqual(result.errors, [])
            with httpfile.read(result.path) as (_, __, headers, body_path):
                self.assertEqual(body_path.read_bytes(), b"A,B\nx,y\nz,a")

    def test_fetch_http_404(self):
        self.mock_http_response = MockHttpResponse(404, [("Content-Length", 0)])
        url = self.build_url("/not-found")
        with call_fetch(url) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        cjwmodule_i18n_message(
                            "http.errors.HttpErrorNotSuccess",
                            {"status_code": 404, "reason": "Not Found"},
                        )
                    )
                ],
            )

    def test_fetch_invalid_url(self):
        with call_fetch("htt://blah") as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        cjwmodule_i18n_message("http.errors.HttpErrorInvalidUrl")
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
        with call_fetch(url1) as result:
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
        with call_fetch(url1) as result:
            self.assertEqual(result.path.read_bytes(), b"")
            self.assertEqual(
                result.errors,
                [
                    RenderError(
                        cjwmodule_i18n_message("http.errors.HttpErrorTooManyRedirects")
                    )
                ],
            )


class RenderTests(unittest.TestCase):
    def test_render_no_file(self):
        table, errors = call_render(P(), None)
        assert_arrow_table_equals(table, None)
        self.assertEqual(errors, [])

    def test_render_fetch_error(self):
        message = I18nMessage("x", {"y": "z"}, None)
        fetch_errors = [RenderError(message)]
        with tempfile_context() as empty_path:
            table, errors = call_render(P(), FetchResult(empty_path, fetch_errors))
            assert_arrow_table_equals(table, None)
            self.assertEqual(errors, [message])

    def test_render_deprecated_parquet(self):
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            table, errors = call_render(P(), FetchResult(fetched_path))
            assert_arrow_table_equals(table, {"A": [1, 2], "B": [3, 4]})
            self.assertEqual(errors, [])

    def test_render_deprecated_parquet_warning(self):
        message = I18nMessage("TODO_i18n", {"text": "truncated table"}, None)
        fetch_errors = [RenderError(message)]
        with parquet_file({"A": [1, 2], "B": [3, 4]}) as fetched_path:
            table, errors = call_render(P(), FetchResult(fetched_path, fetch_errors))
            assert_arrow_table_equals(table, {"A": [1, 2], "B": [3, 4]})
            self.assertEqual(errors, [message])

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
            table, errors = call_render(P(has_header=False), FetchResult(fetched_path))
            assert_arrow_table_equals(table, {"A": [1, 2], "B": [3, 4]})
            self.assertEqual(
                errors, [i18n_message("prompt.disableHeaderHandling",)],
            )

    def test_render_has_header_true(self):
        with tempfile_context(prefix="http-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"A,B\na,b"),
            )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A": ["a"], "B": ["b"]})
            self.assertEqual(errors, [])

    def test_render_has_header_false(self):
        with tempfile_context(prefix="http-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "text/csv")],
                io.BytesIO(b"1,2\n3,4"),
            )
            table, errors = call_render(P(has_header=False), FetchResult(http_path))
            assert_arrow_table_equals(
                table,
                {
                    "Column 1": pyarrow.array([1, 3], pyarrow.int8()),
                    "Column 2": pyarrow.array([2, 4], pyarrow.int8()),
                },
            )
            self.assertEqual(errors, [])

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
                io.BytesIO(b"A;B;C,D\na;b;c,d"),
            )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A;B;C": ["a;b;c"], "D": ["d"]})
            self.assertEqual(errors, [])

    def test_render_csv_use_content_disposition_given_bad_content_type(self):
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/file"},
                "200 OK",
                [
                    ("content-type", "application/octet-stream"),
                    (
                        "content-disposition",
                        'attachment; filename="file.csv"; size=4405',
                    ),
                ],
                # bytes will prove we used "file.csv", not a sniffer.
                io.BytesIO(b"A;B;C,D\na;b;c,d"),
            )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A;B;C": ["a;b;c"], "D": ["d"]})
            self.assertEqual(errors, [])

    def test_render_prefer_content_disposition_to_url_ext(self):
        # When content-disposition uses a different name, prefer that name.
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/file.csv"},
                "200 OK",
                [
                    # Wrong MIME type -- so we detect from filename
                    ("content-type", "application/octet-stream"),
                    ("content-disposition", 'attachment; filename="file.tsv"',),
                ],
                # bytes will prove we used "file.tsv", not "file.csv".
                io.BytesIO(b"A,B\tC,D\na,b\tc,d"),
            )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A,B": ["a,b"], "C,D": ["c,d"]})
            self.assertEqual(errors, [])

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
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A": ["a"], "B": ["b"]})
            self.assertEqual(errors, [])

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
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            assert_arrow_table_equals(table, {"A": ["a"], "B": ["b"]})
            self.assertEqual(errors, [])

    def test_render_json(self):
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", "application/json")],
                io.BytesIO(b'[{"A": "a"}]'),
            )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            self.assertEqual(errors, [])
            assert_arrow_table_equals(table, {"A": ["a"]})

    def test_render_xlsx(self):
        with tempfile_context(prefix="fetch-") as http_path:
            with (TestDataPath / "example.xlsx").open("rb") as xlsx_f:
                httpfile.write(
                    http_path,
                    {"url": "http://example.com/hello"},
                    "200 OK",
                    [("content-type", XLSX_MIME_TYPE)],
                    xlsx_f,
                )
            table, errors = call_render(P(has_header=True), FetchResult(http_path))
            self.assertEqual(errors, [])
            assert_arrow_table_equals(table, {"foo": [1.0, 2.0], "bar": [2.0, 3.0]})

    def test_render_xlsx_bad_content(self):
        with tempfile_context(prefix="fetch-") as http_path:
            httpfile.write(
                http_path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [("content-type", XLSX_MIME_TYPE)],
                io.BytesIO("ceçi n'est pas une .xlsx".encode("utf-8")),
            )
            table, errors = call_render(P(), FetchResult(http_path))
            assert_arrow_table_equals(table, {})
            self.assertEqual(
                errors,
                [
                    I18nMessage(
                        "TODO_i18n",
                        {
                            "text": "Invalid XLSX file: xlnt::exception : failed to find zip header"
                        },
                        None,
                    )
                ],
            )
