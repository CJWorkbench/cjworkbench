import io
import unittest
from unittest import mock
from unittest.mock import patch
import aiohttp
from asgiref.sync import async_to_sync
import pandas as pd
from cjworkbench.types import ProcessResult
from server.modules import scrapetable
from .util import MockParams


P = MockParams.factory(url='', tablenum=1, first_row_is_header=False)


def fetch(**kwargs):
    params = P(**kwargs)
    return async_to_sync(scrapetable.fetch)(params)


class fake_spooled_data_from_url:
    def __init__(self, data=b'', charset='utf-8', error=None):
        self.data = io.BytesIO(data)
        self.headers = {'Content-Type': 'text/html; charset=utf-8'}
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


a_table = pd.DataFrame({
    'A': [1, 2],
    'B': [2, 3]
})


class ScrapeTableTest(unittest.TestCase):
    @patch('server.modules.utils.spooled_data_from_url')
    def test_scrape_table(self, mock_data):
        url = 'http://test.com/tablepage.html'
        mock_data.return_value = fake_spooled_data_from_url(a_table_html)
        fetch_result = fetch(url=url)

        self.assertEqual(mock_data.call_args, mock.call(url))
        self.assertEqual(fetch_result, ProcessResult(a_table))

    def test_first_row_is_header(self):
        # TODO make fetch_result _not_ a pd.DataFrame, so we don't lose info
        # when converting types here
        fetch_result = ProcessResult(pd.DataFrame(a_table.copy()))
        result = scrapetable.render(pd.DataFrame(),
                                    P(first_row_is_header=True),
                                    fetch_result=fetch_result)
        result = ProcessResult.coerce(result)
        expected = pd.DataFrame({'1': [2], '2': [3]})
        self.assertEqual(result, ProcessResult(pd.DataFrame(expected)))

    def test_table_index_under(self):
        url = 'http:INVALID:URL'  # we should never even validate the URL
        fetch_result = fetch(url=url, tablenum=0)
        self.assertEqual(fetch_result, ProcessResult(
            error='Table number must be at least 1'
        ))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(a_table_html))
    def test_table_index_over(self):
        fetch_result = fetch(url='http://example.org', tablenum=2)
        self.assertEqual(fetch_result, ProcessResult(
            error='The maximum table number on this page is 1'
        ))

    def test_invalid_url(self):
        fetch_result = fetch(url='http:NOT:A:URL')
        self.assertEqual(fetch_result, ProcessResult(error='Invalid URL'))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(
               error=aiohttp.ClientResponseError(None, None, status=500,
                                                 message='Server Error')
           ))
    def test_bad_server(self):
        fetch_result = fetch(url='http://example.org')

        self.assertEqual(fetch_result, ProcessResult(
            error='Error from server: 500 Server Error'
        ))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(b'<html><body>No table</body></html>'))
    def test_no_tables(self):
        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = []
            fetch_result = fetch(url='http://example.org')

        self.assertEqual(fetch_result, ProcessResult(
            error='Did not find any <table> tags on that page'
        ))

    @patch('server.modules.utils.spooled_data_from_url',
           fake_spooled_data_from_url(
               error=aiohttp.ClientResponseError(None, None, status=404,
                                                 message='Not Found')
           ))
    def test_404(self):
        fetch_result = fetch(url='http://example.org')
        self.assertEqual(fetch_result, ProcessResult(
            error='Error from server: 404 Not Found'
        ))
