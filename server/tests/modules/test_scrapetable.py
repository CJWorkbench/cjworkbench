import io
import unittest
from unittest import mock
from unittest.mock import patch
import aiohttp
from asgiref.sync import async_to_sync
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.types import ProcessResult
from server.modules import scrapetable
from .util import MockParams


P = MockParams.factory(url="", tablenum=1, first_row_is_header=False)


def fetch(**kwargs):
    params = P(**kwargs)
    return async_to_sync(scrapetable.fetch)(params)


class fake_spooled_data_from_url:
    def __init__(self, data=b"", charset="utf-8", error=None):
        self.data = io.BytesIO(data)
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
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


a_table_html = b"""
<html>
    <body>
        <table>
            <thead><tr><th>A</th><th>B</th></tr></thead>
            <tbody>
                <tr><td>1</td><td>2</td></tr>
                <tr><td>2</td><td>3</td></tr>
            </tbody>
        </table>
    </body>
</html>
"""


a_table = pd.DataFrame({"A": [1, 2], "B": [2, 3]})


class ScrapeTableTest(unittest.TestCase):
    @patch("server.modules.utils.spooled_data_from_url")
    def test_scrape_table(self, mock_data):
        url = "http://test.com/tablepage.html"
        mock_data.return_value = fake_spooled_data_from_url(a_table_html)
        fetch_result = fetch(url=url)

        self.assertEqual(mock_data.call_args, mock.call(url))
        self.assertEqual(fetch_result, ProcessResult(a_table))

    def test_first_row_is_header(self):
        # TODO make fetch_result _not_ a pd.DataFrame, so we don't lose info
        # when converting types here
        fetch_result = ProcessResult(pd.DataFrame(a_table.copy()))
        result = scrapetable.render(
            pd.DataFrame(), P(first_row_is_header=True), fetch_result=fetch_result
        )
        assert_frame_equal(result, pd.DataFrame({"1": [2], "2": [3]}))

    def test_first_row_is_header_zero_rows(self):
        # TODO make fetch_result _not_ a pd.DataFrame
        fetch_result = ProcessResult(pd.DataFrame({"A": [], "B": []}))
        result = scrapetable.render(
            pd.DataFrame(), P(first_row_is_header=True), fetch_result=fetch_result
        )
        assert_frame_equal(result, pd.DataFrame({"A": [], "B": []}))

    def test_first_row_is_header_autocast_dtypes(self):
        # TODO make fetch_result _not_ a pd.DataFrame
        fetch_result = ProcessResult(pd.DataFrame({"A": ["nums", "3"]}))
        result = scrapetable.render(
            pd.DataFrame(), P(first_row_is_header=True), fetch_result=fetch_result
        )
        assert_frame_equal(result, pd.DataFrame({"nums": [3]}))

    def test_first_row_is_header_empty_values(self):
        # TODO make fetch_result _not_ a pd.DataFrame
        fetch_result = ProcessResult(pd.DataFrame({"A": ["", "x"], "B": [2, 3]}))
        result = scrapetable.render(
            pd.DataFrame(), P(first_row_is_header=True), fetch_result=fetch_result
        )
        assert_frame_equal(result, pd.DataFrame({"Column 1": ["x"], "2": [3]}))

    def test_table_index_under(self):
        url = "http:INVALID:URL"  # we should never even validate the URL
        fetch_result = fetch(url=url, tablenum=0)
        self.assertEqual(
            fetch_result, ProcessResult(error="Table number must be at least 1")
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(a_table_html),
    )
    def test_table_index_over(self):
        fetch_result = fetch(url="http://example.org", tablenum=2)
        self.assertEqual(
            fetch_result,
            ProcessResult(error="The maximum table number on this page is 1"),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"""
               <html>
                   <body>
                       <table>
                           <tbody>
                               <tr><th>A</th></tr>
                               <tr><th>a</th><td>1</td></tr>
                               <tr><th>b</th><td>2</td></tr>
                           </tbody>
                       </table>
                   </body>
               </html>
           """
        ),
    )
    def test_only_some_colnames(self):
        # pandas read_table() does odd stuff when there are multiple commas at
        # the ends of rows. Test that read_html() doesn't do the same thing.
        fetch_result = fetch(
            url="http://example.org", tablenum=1, first_row_is_header=True
        )
        assert_frame_equal(
            fetch_result.dataframe,
            pd.DataFrame(
                {"A": ["a", "b"], "Unnamed: 1": [1, 2]}  # TODO should be 'Column 2'?
            ),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            error=aiohttp.ClientResponseError(
                None, None, status=500, message="Server Error"
            )
        ),
    )
    def test_bad_server(self):
        fetch_result = fetch(url="http://example.org")

        self.assertEqual(
            fetch_result, ProcessResult(error="Error from server: 500 Server Error")
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(b"<html><body>No table</body></html>"),
    )
    def test_no_tables(self):
        with mock.patch("pandas.read_html") as readmock:
            readmock.return_value = []
            fetch_result = fetch(url="http://example.org")

        self.assertEqual(
            fetch_result,
            ProcessResult(error="Did not find any <table> tags on that page"),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            error=aiohttp.ClientResponseError(
                None, None, status=404, message="Not Found"
            )
        ),
    )
    def test_404(self):
        fetch_result = fetch(url="http://example.org")
        self.assertEqual(
            fetch_result, ProcessResult(error="Error from server: 404 Not Found")
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"
        ),
    )
    def test_autocast_dtypes(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(fetch_result.dataframe, pd.DataFrame({"A": [1]}))

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            # Add two columns. pd.read_html() will not return an all-empty
            # row, and we're not testing what happens when it does. We want
            # to test what happens when there's an empty _value_.
            b"<table><tr><th>A</th><th>B</th></tr>"
            b"<tr><td>a</td><td></td></tr></table>"
        ),
    )
    def test_empty_str_is_empty_str(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(
            fetch_result.dataframe, pd.DataFrame({"A": ["a"], "B": [""]})
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(b"<html><body><table></table></body></html>"),
    )
    def test_empty_table(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(fetch_result.dataframe, pd.DataFrame({}))
        # BUG: Pandas reports the wrong error message.
        # self.assertEqual(fetch_result.error, 'Table is empty.')
        self.assertEqual(
            fetch_result.error, "Did not find any <table> tags on that page"
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"""
               <html><body><table>
                   <thead><tr><th>A</th></tr></thead>
                   <tbod></tbody>
               </table></body></html>
           """
        ),
    )
    def test_header_only_table(self):
        fetch_result = fetch(url="http://example.org")
        table = fetch_result.dataframe
        assert_frame_equal(fetch_result.dataframe, pd.DataFrame({"A": []}, dtype=str))

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><tr><th>A</th><th>A</th></tr>"
            b"<tr><td>1</td><td>2</td></tr></table>"
        ),
    )
    def test_avoid_duplicate_colnames(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(
            fetch_result.dataframe,
            # We'd prefer 'A 2', but pd.read_html() doesn't give
            # us that choice.
            pd.DataFrame({"A": [1], "A.1": [2]}),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><thead>"
            b'  <tr><th colspan="2">Category</th></tr>'
            b"  <tr><th>A</th><th>B</th></tr>"
            b"</thead><tbody>"
            b"  <tr><td>a</td><td>b</td></tr>"
            b"</tbody></table>"
        ),
    )
    def test_merge_thead_colnames(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(
            fetch_result.dataframe,
            # We'd prefer 'A 2', but pd.read_html() doesn't give
            # us that choice.
            pd.DataFrame({"Category - A": ["a"], "Category - B": ["b"]}),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><tbody><tr><td>a</td><td>b</td></tr></tbody></table>"
        ),
    )
    def test_no_colnames(self):
        fetch_result = fetch(url="http://example.org", first_row_is_header=False)
        assert_frame_equal(
            fetch_result.dataframe,
            # We'd prefer 'A 2', but pd.read_html() doesn't give
            # us that choice.
            pd.DataFrame({"Column 1": ["a"], "Column 2": ["b"]}),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><thead>"
            b'  <tr><th colspan="2">Category</th><th rowspan="2">Category - A</th></tr>'
            b"  <tr><th>A</th><th>B</th></tr>"
            b"</thead><tbody>"
            b"  <tr><td>a</td><td>b</td><td>c</td></tr>"
            b"</tbody></table>"
        ),
    )
    def test_merge_thead_colnames(self):
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(
            fetch_result.dataframe,
            # We'd prefer 'A 2', but pd.read_html() doesn't give
            # us that choice.
            pd.DataFrame(
                {"Category - A": ["a"], "Category - B": ["b"], "Category - A 2": ["c"]}
            ),
        )

    @patch(
        "server.modules.utils.spooled_data_from_url",
        fake_spooled_data_from_url(
            b"<table><thead>"
            b"  <tr><th></th><th>Column 1</th></tr>"
            b"</thead><tbody>"
            b"  <tr><td>a</td><td>b</td><td>c</td></tr>"
            b"</tbody></table>"
        ),
    )
    def test_prevent_empty_colname(self):
        # https://www.pivotaltracker.com/story/show/162648330
        fetch_result = fetch(url="http://example.org")
        assert_frame_equal(
            fetch_result.dataframe,
            pd.DataFrame(
                {
                    # We'd prefer 'Column 1 1', but pd.read_html() doesn't give us that
                    # choice.
                    "Unnamed: 0": ["a"],
                    "Column 1": ["b"],
                    "Unnamed: 2": ["c"],
                }
            ),
        )
