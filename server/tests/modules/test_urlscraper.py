from server.tests.utils import *
from server.modules.urlscraper import *
from server.execute import execute_nocache
from django.test import override_settings
import pandas as pd
import asyncio
import random
import mock
import tempfile
import datetime

# --- Some test data ----

testnow = datetime.datetime.now()
testdate = testnow.strftime('%Y-%m-%d %H:%M:%S')

simple_result_table = pd.DataFrame([
            [ 'http://a.com/file',      testdate,   '200', '<div>all good</div>' ],
            [ 'https://b.com/file2',    testdate,   '404',  ''],
            [ 'http://c.com/file/dir',  testdate,   '200',  '<h1>What a page!</h1>']],
            columns=['url','date','status','html'])

invalid_url_table = simple_result_table.copy()
invalid_url_table.iloc[1, :] = [ 'just not a url', testdate, URLScraper.STATUS_INVALID_URL,  '']

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

    # don't create tasks for invalid urls, because scrape_urls checks before making tasks
    results_tasks = []
    for i in range(len(results)):
        if is_valid_url(results['url'][i]):
            results_tasks.append(
                mock_async_get(results['status'][i], results['html'][i], response_times[i]))

    return results_tasks


class ScrapeUrlsTest(TestCase):
    def setUp(self):
        pass

    # does the hard work for a set of urls/timings/results
    @override_settings(SCRAPER_TIMEOUT=1.1)  # all our test data has 1 second lag max
    def scraper_result_test(self, results, response_times):
        with mock.patch('aiohttp.ClientSession') as session:
            urls = results['url']
            results_tasks = make_test_tasks(results, response_times)
            session_mock = session.return_value  # get the mock obj returned by aoihttp.ClientSession()
            session_mock.get.side_effect = results_tasks

            # mock the output table format scraper expects
            out_table = pd.DataFrame({'url': urls, 'status': ''}, columns=['url', 'status', 'html'])

            event_loop = asyncio.get_event_loop()
            event_loop.run_until_complete(scrape_urls(urls, out_table))

            # ensure that aiohttp.get()_was called with the right sequence of urls
            valid_urls = [x for x in urls if is_valid_url(x)]
            call_urls = []
            for call in session_mock.get.mock_calls:
                name, args, kwargs = call
                call_urls.append(args[0])
            self.assertEqual(call_urls, valid_urls)

            # ensure we saved the right results
            self.assertTrue(out_table['status'].equals(results['status']))
            self.assertTrue(out_table['html'].equals(results['html']))


    # basic tests, where number of urls is smaller than max simultaneous connections
    def test_few_urls(self):
        response_times=[0.5, 0.1, 0.2]
        self.scraper_result_test(simple_result_table, response_times)

        self.scraper_result_test(invalid_url_table, response_times)

        self.scraper_result_test(timeout_table, response_times)

        self.scraper_result_test(no_connection_table, response_times)


    # Case where number of urls much greater than max simultaneous connections. Various errors.
    def test_many_urls(self):

        # make some random, but repeatable test data
        random.seed(42)
        num_urls = 100
        url_range = range(num_urls)

        def random_status():
            p = random.uniform(0, 1)
            if p < 0.1:
                return URLScraper.STATUS_TIMEOUT
            elif p<0.2:
                return URLScraper.STATUS_INVALID_URL
            elif p<0.3:
                return URLScraper.STATUS_NO_CONNECTION
            elif p<0.4:
                return '404'
            else:
                return '200'

        urls = ['https://meh.mydomain%d.com/foofile/%d' % (i,i*43) for i in url_range]
        status = [random_status() for i in url_range ]
        content = [ '<h1>Best headline number %d' % random.randint(1,1000) if status[i]==200 else '' for i in url_range ]
        response_times =[ random.uniform(0,1) for i in url_range ] # seconds before the "server" responds

        results_table = pd.DataFrame({'url':urls, 'date': testdate, 'status':status, 'html':content})

        self.scraper_result_test(results_table, response_times)



# --- Test the URLScraper module ---

# override b/c we depend on StoredObject to transmit data between event() and render(), so make sure not leave files around
@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class URLScraperTests(LoggedInTestCase):
    def setUp(self):
        super(URLScraperTests, self).setUp()  # log in

        self.scraped_table = simple_result_table
        self.urls = list(self.scraped_table['url'])

        # create a workflow that feeds our urls via PasteCSV into a URLScraper
        self.url_table = pd.DataFrame(self.urls, columns=['url'])
        url_csv = 'url\n' + '\n'.join(self.urls)
        workflow = create_testdata_workflow(url_csv)
        self.wfmodule = load_and_add_module('urlscraper', workflow=workflow)


    # send fetch event to button to load data
    def press_fetch_button(self):
        self.client.post('/api/parameters/%d/event' % get_param_by_id_name('version_select').id, {'type': 'click'})

    def test_initial_nop(self):
        out = execute_nocache(self.wfmodule)
        self.assertTrue(out.equals(self.url_table))

    def test_nop_with_initial_col_selection(self):
        # When a column is first selected and no scraping is performed, the initial table should be returned
        source_options = "List of URLs|Load from column".split('|')
        source_pval = get_param_by_id_name('urlsource')
        source_pval.value = source_options.index('Load from column')
        source_pval.save()
        column_pval = get_param_by_id_name('urlcol')
        column_pval.value = 'url'
        column_pval.save()
        out = execute_nocache(self.wfmodule)
        self.assertTrue(out.equals(self.url_table))

    # Simple test that .event() calls scrape_urls() in the right way
    # We don't test all the scrape error cases (invalid urls etc.) as they are tested above
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

        # can't mock datetime.datetime.now with a patch because it's builtin or something, sigh
        URLScraper._mynow = lambda: testnow

        with mock.patch('server.modules.urlscraper.scrape_urls') as scraper:
            scraper.side_effect = mock_scrapeurls # call the mock function instead, the real fn is tested above

            self.press_fetch_button()
            out = execute_nocache(self.wfmodule)
            self.assertTrue(out.equals(self.scraped_table))

    # Tests scraping from a list of URLs
    def test_scrape_list(self):
        source_options = "List|Input column".split('|')
        source_pval = get_param_by_id_name('urlsource')
        source_pval.value = source_options.index('List')
        source_pval.save()

        get_param_by_id_name('urllist').set_value('\n'.join([
            'http://a.com/file',
            'https://b.com/file2',
            'c.com/file/dir' # Removed 'http://' to test the URL-fixing part
        ]))

        # Code below mostly lifted from the column test
        async def mock_scrapeurls(urls, table):
            table['status'] = self.scraped_table['status']
            table['html'] = self.scraped_table['html']
            return

        URLScraper._mynow = lambda: testnow

        with mock.patch('server.modules.urlscraper.scrape_urls') as scraper:
            scraper.side_effect = mock_scrapeurls # call the mock function instead, the real fn is tested above

            self.press_fetch_button()
            out = execute_nocache(self.wfmodule)
            self.assertTrue(out.equals(self.scraped_table))