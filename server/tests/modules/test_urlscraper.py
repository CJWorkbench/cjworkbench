import asyncio
import random
import unittest
from unittest.mock import patch
import aiohttp
from asgiref.sync import async_to_sync
from django.test import override_settings, SimpleTestCase
from django.utils import timezone
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.types import ProcessResult
from server.modules.urlscraper import scrape_urls, URLScraper
from .util import MockParams

# --- Some test data ----

testnow = timezone.now()
testdate = testnow.isoformat(timespec='seconds').replace('+00:00', 'Z')


simple_result_table = pd.DataFrame([
    ['http://a.com/file',      testdate,   '200', '<div>all good</div>'],
    ['https://b.com/file2',    testdate,   '404', ''],
    ['http://c.com/file/dir',  testdate,   '200', '<h1>What a page!</h1>'],
], columns=['url', 'date', 'status', 'html'])

invalid_url_table = pd.DataFrame([
    ['http://a.com/file',      testdate,   '200', '<div>all good</div>'],
    ['just not a url',         testdate,   'Invalid URL', ''],
    ['http://c.com/file/dir',  testdate,   '200', '<h1>What a page!</h1>'],
], columns=['url', 'date', 'status', 'html'])

timeout_table = pd.DataFrame([
    ['http://a.com/file',      testdate,   '200', '<div>all good</div>'],
    ['https://b.com/file2',    testdate,   'Timed out', ''],
    ['http://c.com/file/dir',  testdate,   '200', '<h1>What a page!</h1>'],
], columns=['url', 'date', 'status', 'html'])

no_connection_table = pd.DataFrame([
    ['http://a.com/file',      testdate,   '200', '<div>all good</div>'],
    ['https://b.com/file2',    testdate,   "Can't connect: blah", ''],
    ['http://c.com/file/dir',  testdate,   '200', '<h1>What a page!</h1>'],
], columns=['url', 'date', 'status', 'html'])

url_table = simple_result_table.loc[0:, ['url']].copy()


# mock for aiohttp.ClientResponse. Note async text()
class MockResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text


class MockCachedRenderResult:
    def __init__(self, dataframe: pd.DataFrame):
        self.result = ProcessResult(dataframe)


# this replaces aiohttp.get. Wait for a lag, then a test response
# If the status is an error, throw the appropriate exception
async def mock_async_get(status, text, lag):
    await asyncio.sleep(lag)

    if status == 'Timed out':
        raise asyncio.TimeoutError
    elif status == 'Invalid URL':
        raise aiohttp.InvalidURL()
    elif status == "Can't connect: blah":
        raise aiohttp.client_exceptions.ClientConnectionError('blah')

    return MockResponse(status, text)


P = MockParams.factory(urlsource=0, urllist='', urlcol='')


def fetch(params, input_dataframe):
    async def get_input_dataframe():
        return input_dataframe

    return async_to_sync(URLScraper.fetch)(
        params,
        get_input_dataframe=get_input_dataframe
    )


class ScrapeUrlsTest(SimpleTestCase):
    # does the hard work for a set of urls/timings/results
    @override_settings(SCRAPER_TIMEOUT=0.2)  # all our test data lags 0.25s max
    def scraper_result_test(self, results, response_times):
        async def session_get(url, *, timeout=None):
            # Silly mock HTTP GET computes the test's input based on its
            # expected output. This defeats the purpose of a test.
            row = results[results['url'] == url]
            if row.empty:
                raise ValueError('called with URL we did not expect')
            index = row.index[0]
            delay = response_times[index]
            await asyncio.sleep(delay)

            status = row.at[index, 'status']
            text = row.at[index, 'html']

            if status == 'Timed out':
                raise asyncio.TimeoutError
            elif status == 'Invalid URL':
                raise aiohttp.InvalidURL(url)
            elif status == "Can't connect: blah":
                raise aiohttp.client_exceptions.ClientConnectionError('blah')
            else:
                return MockResponse(int(status), text)

        with patch('aiohttp.ClientSession') as session:
            urls = results['url'].tolist()
            session_mock = session.return_value
            session_mock.get.side_effect = session_get

            # mock the output table format scraper expects
            out_table = pd.DataFrame(
                data={'url': urls, 'status': ''},
                columns=['url', 'status', 'html']
            )

            event_loop = asyncio.get_event_loop()
            event_loop.run_until_complete(scrape_urls(urls, out_table))

            assert_frame_equal(
                out_table[['url', 'status', 'html']],
                results[['url', 'status', 'html']]
            )

            # ensure aiohttp.get() called with the right sequence of urls
            call_urls = [args[0] for name, args, kwargs
                         in session_mock.get.mock_calls]
            self.assertEqual(set(call_urls), set(urls))

    # basic tests, number of urls smaller than max simultaneous connections
    def test_simple_urls(self):
        response_times = [0.005, 0.002, 0.008]
        self.scraper_result_test(simple_result_table, response_times)

    def test_invalid_url(self):
        response_times = [0.005, 0.002, 0.008]
        self.scraper_result_test(invalid_url_table, response_times)

    def test_timeout_url(self):
        response_times = [0.005, 0.002, 0.008]
        self.scraper_result_test(timeout_table, response_times)

    def test_no_connection_url(self):
        response_times = [0.005, 0.002, 0.008]
        self.scraper_result_test(no_connection_table, response_times)

    # Number of urls greater than max simultaneous connections.
    # Various errors.
    def test_many_urls(self):
        # make some random, but repeatable test data
        random.seed(42)
        num_urls = 20
        url_range = range(num_urls)

        def random_status():
            p = random.uniform(0, 1)
            if p < 0.1:
                return 'Timed out'
            elif p < 0.2:
                return 'Invalid URL'
            elif p < 0.3:
                return "Can't connect: blah"
            elif p < 0.4:
                return '404'
            else:
                return '200'

        urls = [f'https://example{i}.com/foofile/{i * 43}' for i in url_range]
        status = [random_status() for i in url_range]
        content = [f'<h1>Headline {i}</h1>' if status[i] == '200' else ''
                   for i in url_range]

        # seconds before the "server" responds
        response_times = [random.uniform(0, 0.002) for i in url_range]

        results_table = pd.DataFrame({
            'url': urls,
            'date': testdate,
            'status': status,
            'html': content,
        })

        self.scraper_result_test(results_table, response_times)

    def test_module_initial_nop(self):
        table = pd.DataFrame({'A': [1]})
        result = URLScraper.render(P(urlsource=0, urllist=''), table.copy(),
                                   fetch_result=None)
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, table)

    def test_module_nop_with_initial_col_selection(self):
        table = pd.DataFrame({'A': [1]})
        result = URLScraper.render(P(urlsource=1, urlcol=''), table.copy(),
                                   fetch_result=None)
        self.assertEqual(result.error, '')
        assert_frame_equal(result.dataframe, table)


class URLScraperTests(unittest.TestCase):
    # Simple test that .fetch() calls scrape_urls() in the right way
    # We don't test all the scrape error cases (invalid urls etc.) as they are
    # tested above
    def test_scrape_column(self):
        scraped_table = simple_result_table.copy()

        # modifies the table in place to add results, just like the real thing
        async def mock_scrapeurls(urls, table):
            table['status'] = scraped_table['status']
            table['html'] = scraped_table['html']
            return

        urls = list(simple_result_table['url'])

        with patch('django.utils.timezone.now', lambda: testnow):
            with patch('server.modules.urlscraper.scrape_urls') as scrape:
                # call the mock function instead, the real fn is tested above
                scrape.side_effect = mock_scrapeurls

                result = fetch(P(urlsource=1, urlcol='x'),
                               pd.DataFrame({'x': urls}))
                self.assertEqual(result, ProcessResult(scraped_table))

    # Tests scraping from a list of URLs
    def test_scrape_list(self):
        scraped_table = simple_result_table.copy()

        # Code below mostly lifted from the column test
        async def mock_scrapeurls(urls, table):
            table['status'] = scraped_table['status']
            table['html'] = scraped_table['html']
            return

        with patch('django.utils.timezone.now', lambda: testnow):
            with patch('server.modules.urlscraper.scrape_urls') as scrape:
                # call the mock function instead, the real fn is tested above
                scrape.side_effect = mock_scrapeurls

                result = fetch(P(urlsource=0, urllist='\n'.join([
                    'http://a.com/file',
                    'https://b.com/file2',
                    'c.com/file/dir'  # Removed 'http://' to test URL-fixing
                ])), None)
                self.assertEqual(result, ProcessResult(scraped_table))
