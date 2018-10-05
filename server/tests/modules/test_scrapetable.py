import unittest
from unittest import mock
from asgiref.sync import async_to_sync
import pandas as pd
from urllib.error import URLError, HTTPError
from server.modules.scrapetable import ScrapeTable
from server.modules.types import ProcessResult
from .util import MockParams, fetch_factory


P = MockParams.factory(url='', tablenum=1, first_row_is_header=False)
fetch = fetch_factory(ScrapeTable.event, P)


def render(wf_module):
    if hasattr(wf_module, 'fetch_result'):
        fetch_result = wf_module.fetch_result
    else:
        fetch_result = None

    result = ScrapeTable.render(wf_module.get_params(), pd.DataFrame(),
                                fetch_result=fetch_result)
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
        fetch_result = ProcessResult(pd.DataFrame(a_table.copy()))
        result = ScrapeTable.render(P(first_row_is_header=True),
                                    pd.DataFrame(),
                                    fetch_result=fetch_result)
        result = ProcessResult.coerce(result)
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
