import asyncio
import random
import tempfile
from unittest import mock
import aiohttp
from django.test import override_settings
from django.utils import timezone
import pandas as pd
from server.tests.utils import DbTestCase, LoggedInTestCase, \
        create_testdata_workflow, load_and_add_module, get_param_by_id_name
# TODO do not import is_valid_url -- it's code under test, not code used _by_
# tests
from server.modules.types import ProcessResult
from server.modules.urlscraper import URLScraper, is_valid_url, scrape_urls
from server.execute import execute_wfmodule

# --- Some test data ----

testnow = timezone.now()
testdate = testnow.isoformat(timespec='seconds').replace('+00:00', 'Z')


simple_result_table = pd.DataFrame([
    ['http://a.com/file',      testdate,   '200', '<div>all good</div>'],
    ['https://b.com/file2',    testdate,   '404', ''],
    ['http://c.com/file/dir',  testdate,   '200', '<h1>What a page!</h1>'],
], columns=['url', 'date', 'status', 'html'])

invalid_url_table = simple_result_table.copy()
invalid_url_table.iloc[1, :] = [
    'just not a url',
    testdate,
    URLScraper.STATUS_INVALID_URL,
    '',
]

timeout_table = simple_result_table.copy()
timeout_table.iloc[1, 2] = URLScraper.STATUS_TIMEOUT

no_connection_table = simple_result_table.copy()
no_connection_table.iloc[1, 2] = URLScraper.STATUS_NO_CONNECTION


# --- Test our async multiple url scraper ---

# this replaces aiohttp.get. Wait for a lag, then a test response
# If the status is an error, throw the appropriate exception
async def mock_async_get(status, text, lag):
    await asyncio.sleep(lag)

    if status == URLScraper.STATUS_TIMEOUT:
        raise asyncio.TimeoutError
    elif status == URLScraper.STATUS_NO_CONNECTION:
        raise aiohttp.client_exceptions.ClientConnectionError

    # mock for aiohttp.ClientResponse. Note async text()
    class MockResponse:
        def __init__(self, status, text):
            self.status = status
            self._text = text

        async def text(self):
            return self._text

    return MockResponse(status, text)


# Table of urls and correct responses to a set of tasks
def make_test_tasks(results, response_times):
    # don't create tasks for invalid urls, because scrape_urls checks before
    # making tasks
    results_tasks = []
    for i in range(len(results)):
        if is_valid_url(results['url'][i]):
            results_tasks.append(
                mock_async_get(
                    results['status'][i],
                    results['html'][i],
                    response_times[i]
                )
            )

    return results_tasks


class ScrapeUrlsTest(DbTestCase):
    # does the hard work for a set of urls/timings/results
    @override_settings(SCRAPER_TIMEOUT=0.2)  # all our test data lags 0.25s max
    def scraper_result_test(self, results, response_times):
        with mock.patch('aiohttp.ClientSession') as session:
            urls = results['url']
            results_tasks = make_test_tasks(results, response_times)
            # get the mock obj returned by aoihttp.ClientSession()
            session_mock = session.return_value
            session_mock.get.side_effect = results_tasks

            # mock the output table format scraper expects
            out_table = pd.DataFrame(
                data={'url': urls, 'status': ''},
                columns=['url', 'status', 'html']
            )

            event_loop = asyncio.get_event_loop()
            event_loop.run_until_complete(scrape_urls(urls, out_table))

            # ensure aiohttp.get() called with the right sequence of urls
            valid_urls = [x for x in urls if is_valid_url(x)]
            call_urls = []
            for call in session_mock.get.mock_calls:
                name, args, kwargs = call
                call_urls.append(args[0])
            self.assertEqual(call_urls, valid_urls)

            # ensure we saved the right results
            self.assertTrue(out_table['status'].equals(results['status']))
            self.assertTrue(out_table['html'].equals(results['html']))

    # basic tests, number of urls smaller than max simultaneous connections
    def test_few_urls(self):
        response_times = [0.05, 0.02, 0.08]
        self.scraper_result_test(simple_result_table, response_times)

        self.scraper_result_test(invalid_url_table, response_times)

        self.scraper_result_test(timeout_table, response_times)

        self.scraper_result_test(no_connection_table, response_times)

    # Number of urls greater than max simultaneous connections.
    # Various errors.
    def test_many_urls(self):

        # make some random, but repeatable test data
        random.seed(42)
        num_urls = 100
        url_range = range(num_urls)

        def random_status():
            p = random.uniform(0, 1)
            if p < 0.1:
                return URLScraper.STATUS_TIMEOUT
            elif p < 0.2:
                return URLScraper.STATUS_INVALID_URL
            elif p < 0.3:
                return URLScraper.STATUS_NO_CONNECTION
            elif p < 0.4:
                return '404'
            else:
                return '200'

        urls = [f'https://example{i}.com/foofile/{i * 43}' for i in url_range]
        status = [random_status() for i in url_range]
        content = [f'<h1>Headline {i}</h1>' if status[i] == 200 else ''
                   for i in url_range]

        # seconds before the "server" responds
        response_times = [random.uniform(0, 0.01) for i in url_range]

        results_table = pd.DataFrame({
            'url': urls,
            'date': testdate,
            'status': status,
            'html': content,
        })

        self.scraper_result_test(results_table, response_times)


# override b/c we depend on StoredObject to transmit data between event() and
# render(), so make sure not leave files around
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class URLScraperTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()  # log in

        self.scraped_table = simple_result_table
        self.urls = list(self.scraped_table['url'])

        # create a workflow that feeds our urls via PasteCSV into a URLScraper
        self.url_table = pd.DataFrame(self.urls, columns=['url'])
        self.expected_url_table_result = ProcessResult(self.url_table)
        self.expected_url_table_result.sanitize_in_place()

        url_csv = 'url\n' + '\n'.join(self.urls)
        workflow = create_testdata_workflow(url_csv)
        self.wfmodule = load_and_add_module('urlscraper', workflow=workflow)

    def press_fetch_button(self):
        version_id = get_param_by_id_name('version_select').id
        self.client.post(f'/api/parameters/{version_id}/event')

    def test_initial_nop(self):
        result = execute_wfmodule(self.wfmodule)
        self.assertEqual(result, self.expected_url_table_result)

    def test_nop_with_initial_col_selection(self):
        # When a column is first selected and no scraping is performed, the
        # initial table should be returned
        source_options = "List of URLs|Load from column".split('|')
        source_pval = get_param_by_id_name('urlsource')
        source_pval.value = source_options.index('Load from column')
        source_pval.save()
        column_pval = get_param_by_id_name('urlcol')
        column_pval.value = 'url'
        column_pval.save()
        result = execute_wfmodule(self.wfmodule)
        self.assertEqual(result, self.expected_url_table_result)

    # Simple test that .event() calls scrape_urls() in the right way
    # We don't test all the scrape error cases (invalid urls etc.) as they are
    # tested above
    def test_scrape_column(self):
        source_options = "List|Input column".split('|')
        source_pval = get_param_by_id_name('urlsource')
        source_pval.value = source_options.index('Input column')
        source_pval.save()

        get_param_by_id_name('urlcol').set_value('url')

        # modifies the table in place to add results, just like the real thing
        async def mock_scrapeurls(urls, table):
            table['status'] = self.scraped_table['status']
            table['html'] = self.scraped_table['html']
            return

        with mock.patch('django.utils.timezone.now') as now:
            now.return_value = testnow

            with mock.patch('server.modules.urlscraper.scrape_urls') as scrape:
                # call the mock function instead, the real fn is tested above
                scrape.side_effect = mock_scrapeurls

                self.press_fetch_button()
                result = execute_wfmodule(self.wfmodule)
                self.assertEqual(result, ProcessResult(self.scraped_table))

    # Tests scraping from a list of URLs
    def test_scrape_list(self):
        source_options = "List|Input column".split('|')
        source_pval = get_param_by_id_name('urlsource')
        source_pval.value = source_options.index('List')
        source_pval.save()

        get_param_by_id_name('urllist').set_value('\n'.join([
            'http://a.com/file',
            'https://b.com/file2',
            'c.com/file/dir'  # Removed 'http://' to test the URL-fixing part
        ]))

        # Code below mostly lifted from the column test
        async def mock_scrapeurls(urls, table):
            table['status'] = self.scraped_table['status']
            table['html'] = self.scraped_table['html']
            return

        with mock.patch('django.utils.timezone.now') as now:
            now.return_value = testnow

            with mock.patch('server.modules.urlscraper.scrape_urls') as scrape:
                # call the mock function instead, the real fn is tested above
                scrape.side_effect = mock_scrapeurls

                self.press_fetch_button()
                result = execute_wfmodule(self.wfmodule)
                self.assertEqual(result, ProcessResult(self.scraped_table))
