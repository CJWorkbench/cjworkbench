import unittest
from unittest import mock
from asgiref.sync import async_to_sync
import pandas as pd
from urllib.error import URLError, HTTPError
from server.modules.scrapetable import ScrapeTable
from server.modules.types import ProcessResult


class MockWfModule:
    def __init__(self, url='', tablenum=1, first_row_is_header=False):
        self.url = url
        self.tablenum = tablenum
        self.first_row_is_header = first_row_is_header
        self.fetched_result = None
        self.fetch_error = ''

    def get_param_checkbox(self, _):
        return self.first_row_is_header

    def get_param_string(self, _):
        return self.url

    def get_param_integer(self, _):
        return self.tablenum

    def retrieve_fetched_table(self):
        if self.fetched_result:
            return self.fetched_result.dataframe
        else:
            return None


async def _commit(wf_module, result, json=None):
    wf_module.fetched_result = result
    wf_module.fetch_error = result.error


@mock.patch('server.modules.moduleimpl.ModuleImpl.commit_result', _commit)
def fetch(*args, **kwargs):
    wf_module = MockWfModule(*args, **kwargs)
    async_to_sync(ScrapeTable.event)(wf_module)
    return wf_module


def render(wf_module):
    result = ScrapeTable.render(wf_module, pd.DataFrame())
    result = ProcessResult.coerce(result)
    return result


a_table = pd.DataFrame({
    'A': [1, 2],
    'B': [2, 3]
})


class ScrapeTableTest(unittest.TestCase):
    def test_scrape_table(self):
        url = 'http://test.com/tablepage.html'
        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = [a_table.copy()]
            wf_module = fetch(url=url)

            self.assertEqual(readmock.call_args,
                             mock.call(url, flavor='html5lib'))

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(a_table))

    def test_first_row_is_header(self):
        wf_module = MockWfModule(url='http://example.com',
                                 first_row_is_header=True)
        wf_module.fetched_result = ProcessResult(a_table.copy())

        result = render(wf_module)
        expected = pd.DataFrame({'1': [2], '2': [3]})
        self.assertEqual(result, ProcessResult(pd.DataFrame(expected)))

    def test_table_index_under(self):
        url = 'http://test.com/tablepage.html'
        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = [a_table.copy()]
            wf_module = fetch(url=url, tablenum=0)

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(
            error='Table number must be at least 1'
        ))

    def test_table_index_over(self):
        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = [a_table.copy(), a_table.copy()]
            wf_module = fetch(url='http://example.org', tablenum=3)

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(
            error='The maximum table number on this page is 2'
        ))

    def test_invalid_url(self):
        wf_module = fetch(url='not a url')
        result = render(wf_module)
        self.assertEqual(result, ProcessResult(error='Invalid URL'))

    def test_bad_server(self):
        with mock.patch('pandas.read_html') as readmock:
            readmock.side_effect = URLError('Server error')
            wf_module = fetch(url='http://example.org')

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(
            error='<urlopen error Server error>'
        ))

    def test_no_tables(self):
        with mock.patch('pandas.read_html') as readmock:
            readmock.return_value = []
            wf_module = fetch(url='http://example.org')

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(
            error='Did not find any <table> tags on that page'
        ))

    def test_404(self):
        with mock.patch('pandas.read_html') as readmock:
            readmock.side_effect = HTTPError('http://example.org', 404,
                                             "fake error message", None, None)
            wf_module = fetch(url='http://example.org')

        result = render(wf_module)
        self.assertEqual(result, ProcessResult(error='Page not found (404)'))
