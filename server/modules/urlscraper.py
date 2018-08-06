import aiohttp
import asyncio
import re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
import pandas as pd
from .moduleimpl import ModuleImpl
from .types import ProcessResult


# --- Asynchornous URL scraping ---

# get or create an event loop for the current thread.
def get_thread_event_loop():
    try:
        loop = asyncio.get_event_loop()  # try to get previously set event loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def is_valid_url(url):
    validate = URLValidator()
    try:
        validate(url)
        return True
    except ValidationError:
        return False


async def async_get_url(url):
    """Returns a Future { 'status': ..., 'text': ... } dict.

    The Future will resolve within settings.SCRAPER_TIMEOUT seconds: either
    to a dict, an asyncio.TimeoutError, or an
    aiohttp.client_exceptions.ClientError. (The most obvious ClientError is
    ClientConnectionError, but there are others.)
    """
    session = aiohttp.ClientSession()
    response = await session.get(url, timeout=settings.SCRAPER_TIMEOUT)
    # We have the header. Now read the content.
    # response.text() times out according to SCRAPER_TIMEOUT above. See
    # https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
    text = await response.text()
    return {'status': response.status, 'text': text}


# Parses the HTTP response object and stores it as a row in our table
def add_result_to_table(table, i, response):
    table.loc[i,'status'] = str(response['status'])
    table.loc[i,'html'] = response['text']


# Server didn't get back to us in time
def add_error_to_table(table, i, errmsg):
    table.loc[i,'status'] = errmsg
    table.loc[i,'html'] = ''


# Asynchronously scrape many urls, and store the results in the table
async def scrape_urls(urls, result_table):
    event_loop = get_thread_event_loop()

    max_fetchers = settings.SCRAPER_NUM_CONNECTIONS

    tasks_to_rows = {}  # double as our list of currently active tasks
    num_urls = len(urls)
    started_urls = 0
    finished_urls = 0

    while finished_urls < num_urls:

        # start tasks until we max out connections, or run out of urls
        while ( len(tasks_to_rows) < max_fetchers ) and ( started_urls < num_urls ):
            url = urls[started_urls].strip()
            if is_valid_url(url):
                newtask = event_loop.create_task(async_get_url(url))
                tasks_to_rows[newtask] = started_urls
            else:
                add_error_to_table(result_table, started_urls, URLScraper.STATUS_INVALID_URL)
                finished_urls += 1
            started_urls += 1

        # Wait for any of the fetches to finish (if there are any)
        if len(tasks_to_rows) > 0:
            finished, pending = await asyncio.wait(tasks_to_rows.keys(), return_when=asyncio.FIRST_COMPLETED)

            # process any results we got
            for task in finished:
                try:
                    response = task.result()
                    add_result_to_table(result_table, tasks_to_rows[task], response)
                except asyncio.TimeoutError:
                    add_error_to_table(result_table, tasks_to_rows[task], URLScraper.STATUS_TIMEOUT)
                except aiohttp.client_exceptions.ClientConnectionError:
                    add_error_to_table(result_table, tasks_to_rows[task], URLScraper.STATUS_NO_CONNECTION)

                del tasks_to_rows[task]

            finished_urls += len(finished)



# --- URLScraper module ---

class URLScraper(ModuleImpl):
    STATUS_INVALID_URL = "Invalid URL"
    STATUS_TIMEOUT = "No response"
    STATUS_NO_CONNECTION = "Can't connect"

    @staticmethod
    def render(wf_module, table):
        urlsource = wf_module.get_param_menu_string('urlsource')
        if urlsource == 'Input column':
            urlcol = wf_module.get_param_column('urlcol')
            if urlcol != '':
                # Check if we have a fetched table; if not, return the table itself.
                fetched_table = wf_module.retrieve_fetched_table()
                if fetched_table is not None:
                    return (fetched_table, wf_module.error_msg)
                return table
            else:
                return table # nop if column not set
        elif urlsource == 'List':
            fetched_table = wf_module.retrieve_fetched_table()
            if fetched_table is not None:
                return (fetched_table, wf_module.error_msg)
            else:
                return table

    # Scrapy scrapy scrapy
    #
    # TODO this should be in .render(), right?
    @staticmethod
    def event(wfm, **kwargs):
        # fetching could take a while so notify clients/users we're working
        wfm.set_busy()

        urls = []
        urlsource = wfm.get_param_menu_string('urlsource')

        if urlsource == 'List':
            urllist_text = wfm.get_param_string('urllist')
            urllist_raw = urllist_text.split('\n')
            for url in urllist_raw:
                s_url = url.strip()
                if len(s_url) == 0:
                    continue
                # Fix in case user adds an URL without http(s) prefix
                if not re.match('^https?://.*', s_url):
                    urls.append('http://{}'.format(s_url))
                else:
                    urls.append(s_url)
        elif urlsource == 'Input column':
            # get our list of URLs from a column in the input table
            urlcol = wfm.get_param_column('urlcol')
            if urlcol == '':
                return
            from server.execute import execute_wfmodule
            prev_table = execute_wfmodule(wfm.previous_in_stack()).dataframe

            # column parameters are not sanitized here, could be missing
            # this col
            if urlcol in prev_table.columns:
                urls = prev_table[urlcol].tolist()

        if len(urls) > 0:
            table = pd.DataFrame(
                {'url': urls, 'status': ''},
                columns=['url', 'date', 'status', 'html']
            )

            event_loop = get_thread_event_loop()
            event_loop.run_until_complete(scrape_urls(urls, table))

        else:
            table = pd.DataFrame()

        table['date'] = timezone.now().isoformat(timespec='seconds') \
                .replace('+00:00', 'Z')

        result = ProcessResult(dataframe=table)
        # No need to truncate: input is already truncated
        # No need to sanitize: we only added text+date+status

        ModuleImpl.commit_result(wfm, result)
