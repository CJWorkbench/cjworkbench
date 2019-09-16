import io
import unittest
from unittest.mock import patch
import aiohttp
from asgiref.sync import async_to_sync
import pandas as pd
from pandas.testing import assert_frame_equal
import requests
from cjwkernel.pandas.types import ProcessResult
from server.modules import loadurl
from cjwstate.tests.utils import mock_xlsx_path
from .util import MockParams

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

mock_csv_raw = b"Month,Amount\nJan,10\nFeb,20"
mock_csv_table = pd.DataFrame({"Month": ["Jan", "Feb"], "Amount": [10, 20]})


class fake_spooled_data_from_url:
    def __init__(self, data=b"", content_type="", charset="utf-8", error=None):
        self.data = io.BytesIO(data)
        self.headers = {"Content-Type": content_type}
        self.charset = charset
        self.error = error

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        if self.error:
            raise self.error
        else:
            return (self.data, self.headers, self.charset)
        return self

    async def __aexit__(self, *args):
        return


def mock_text_response(text, content_type):
    response = requests.Response()
    response.encoding = "utf-8"
    response.headers["Content-Type"] = content_type
    # In requests, `response.raw` does not behave like a file-like object
    # as we would expect. But it does happen to give us a correct
    # `response.content` in the code that uses that.
    response.raw = io.BytesIO(text.encode("utf-8"))
    response.reason = "OK"
    response.status_code = 200
    return response


def mock_bytes_response(b, content_type):
    response = requests.Response()
    response.headers["Content-Type"] = content_type
    response.raw = io.BytesIO(b)
    response.reason = "OK"
    response.status_code = 200
    return response


def respond(str_or_bytes, content_type):
    def r(*args, **kwargs):
        if isinstance(str_or_bytes, str):
            return mock_text_response(str_or_bytes, content_type)
        else:
            return mock_bytes_response(str_or_bytes, content_type)

    return r


P = MockParams.factory(url="", has_header=True)


def fetch(**kwargs):
    params = P(**kwargs)
    return async_to_sync(loadurl.fetch)(params)


class LoadUrlTests(unittest.TestCase):
    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(mock_csv_raw, "text/csv"),
    )
    def test_fetch_csv(self):
        result = fetch(url="http://test.com/the.csv")
        assert_frame_equal(result, mock_csv_table)

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(b'a\n"b', "text/csv"),
    )
    def test_fetch_invalid_csv(self):
        # It would be great to report "warnings" on invalid input. But Python's
        # `csv` module won't do that: it forces us to choose between mangling
        # input and raising an exception. Both are awful; mangling input is
        # slightly preferable, so that's what we do.
        result = fetch(url="http://test.com/the.csv")
        assert_frame_equal(result, pd.DataFrame({"a": ["b"]}))

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(mock_csv_raw, "text/plain"),
    )
    def test_fetch_csv_use_ext_given_bad_content_type(self):
        # return text/plain type and rely on filename detection, as
        # https://raw.githubusercontent.com/ does
        result = fetch(url="http://test.com/the.csv")
        assert_frame_equal(result, mock_csv_table)

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(mock_csv_raw, "application/csv"),
    )
    def test_fetch_csv_handle_nonstandard_mime_type(self):
        """
        Transform 'application/csv' into 'text/csv', etc.

        Sysadmins sometimes invent MIME types and we can infer exactly what
        they _mean_, even if they didn't say it.
        """
        result = fetch(url="http://test.com/the.data?format=csv&foo=bar")
        assert_frame_equal(result, mock_csv_table)

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(b'[{"A":1}]', "application/json", "utf-8"),
    )
    def test_fetch_json(self):
        result = fetch(url="http://test.com/the.json")
        assert_frame_equal(result, pd.DataFrame({"A": [1]}))

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(b"not json", "application/json"),
    )
    def test_fetch_json_invalid_json(self):
        result = fetch(url="http://test.com/the.json")
        self.assertEqual(
            result["error"], "JSON lexical error: invalid string in json text."
        )

    def test_fetch_xlsx(self):
        with open(mock_xlsx_path, "rb") as f:
            xlsx_bytes = f.read()
            xlsx_table = pd.read_excel(mock_xlsx_path)

        with patch(
            "cjwkernel.pandas.moduleutils.spooled_data_from_url",
            fake_spooled_data_from_url(xlsx_bytes, XLSX_MIME_TYPE, None),
        ):
            result = fetch(url="http://test.com/x.xlsx")
        assert_frame_equal(result, xlsx_table)

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(b"hi", XLSX_MIME_TYPE, None),
    )
    def test_fetch_xlsx_bad_content(self):
        result = fetch(url="http://test.com/x.xlsx")
        self.assertEqual(
            result,
            (
                "Error reading Excel file: Unsupported format, or corrupt "
                "file: Expected BOF record; found b'hi'"
            ),
        )

    @patch(
        "cjwkernel.pandas.moduleutils.spooled_data_from_url",
        fake_spooled_data_from_url(
            error=aiohttp.ClientResponseError(
                None, None, status=404, message="Not Found"
            )
        ),
    )
    def test_load_404(self):
        # 404 error should put module in error state
        fetch_result = fetch(url="http://example.org/x.csv")
        self.assertEqual(
            fetch_result, ProcessResult(error="Error from server: 404 Not Found")
        )

    def test_bad_url(self):
        fetch_result = fetch(url="not a url")
        self.assertEqual(fetch_result, ProcessResult(error="Invalid URL"))
