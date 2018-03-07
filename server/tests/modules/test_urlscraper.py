from server.tests.utils import *
from server.modules.urlscraper import scrape_urls, is_valid_url
from django.test import override_settings
import pandas as pd
import asyncio
import random
import mock


# this replaces aiohttp.get with a lag then a test response
async def mock_async_get(lag, response):
    await asyncio.sleep(lag)
    return response

# Mocked response to getting each URL. Short to preent a long test
def make_response(status, html):
    return {'status': status, 'text': html}

# turn a test urls/results list into a set of mock tasks, as well as other useful bits
def make_test_tasks(results):
    results_status = [str(x[1]['status']) for x in results]  # scrape_urls() should return string statuses
    results_content = [x[1]['text'] for x in results]
    results_tasks = [mock_async_get(x[0], x[1]) for x in results]
    return results_tasks, results_status, results_content

class ScrapeUrlsTest(TestCase):
    def setUp(self):
        pass

    # does the hard work for a set of urls/timings/results
    @override_settings(SCRAPER_TIMEOUT=1.1)  # all our test data has 1 second lag max
    def scraper_result_test(self, urls, results):
        with mock.patch('aiohttp.ClientSession') as session:
            results_tasks, results_status, results_content = make_test_tasks(results)

            session_mock = session.return_value  # get the mock obj returned by aoihttp.ClientSession()
            session_mock.get.side_effect = [results_tasks[i] for i in range(len(urls)) if is_valid_url(urls[i])]

            # mock the output table format it expects
            out_table = pd.DataFrame({'urls': urls, 'status': ''}, columns=['urls', 'status', 'html'])

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
            self.assertTrue(out_table['status'].equals(pd.Series(results_status)))
            self.assertTrue(out_table['html'].equals(pd.Series(results_content)))


    # basic test, where number of urls is smaller than max simultaneous connections
    def test_few_urls(self):
        urls_small = ['http://a.com/file', 'https://b.com/file2', 'http://c.com/file/dir']
        results_small = [
            (0.5, make_response(200, '<div>all good</div>')),
            (0.1, make_response(404, None)),
            (0.2, make_response(200, '<h1>What a page!</h1>'))
        ]

        self.scraper_result_test(urls_small, results_small)

        # make one of the URLs invalid
        urls_small[1] = 'just not a url'
        results_small[1] = (0.1, make_response('Invalid URL', ''))
        self.scraper_result_test(urls_small, results_small)



    # Case where number of urls much greater than max simultaneous connections. Also, timeouts
    def test_many_urls(self):
        num_big = 100
        urls_big = ['https://meh.mydomain%d.com/foofile/%d' % (i,i*43) for i in range(num_big)]

        random.seed(42) # random, but always the same, so that test fails are reproducible
        response_times =[ random.uniform(0,1) for i in range(num_big) ] # seconds before the "server" responds
        response_status = [ 200 if random.uniform(0,1)>0.2 else 404 for i in range(num_big) ]
        response_content = [ '<h1>Best headline number %d' % random.randint(1,1000) if response_status[i]==200 else '' for i in range(num_big)]
        results_big = list(zip(response_times,
                           [make_response(response_status[i], response_content[i]) for i in range(num_big)]))

        self.scraper_result_test(urls_big, results_big)

        # now get fiendish and make some of the urls time out
        for foo in range(20):
            i = random.randint(0, num_big)
            response_times[i] = 1000 # nope
            response_status[i] = 'No response'
            response_content[i] = ''

        results_timeout = list( zip(response_times,
                                [make_response(response_status[i], response_content[i]) for i in range(num_big)]))

        self.scraper_result_test(urls_big, results_timeout)

