from .moduleimpl import ModuleImpl
import pandas as pd
from server.versions import save_fetched_table_if_changed
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.conf import settings
import aiohttp
import asyncio

event_loop = asyncio.get_event_loop()

def is_valid_url(url):
    validate = URLValidator()
    try:
        validate(url)
        return True
    except ValidationError:
        return False

async def async_get_url(url):
    with aiohttp.Timeout(settings.SCRAPER_TIMEOUT):
        session = aiohttp.ClientSession()
        return await session.get(url)

# Parses the HTTP response object and stores it as a row in our table
def add_result_to_table(table, i, response):
    table.loc[i,'status'] = str(response['status'])
    table.loc[i,'html'] = response['text']


# Server didn't get back to us in time
def add_timeout_to_table(table, i):
    table.loc[i,'status'] = 'No response'
    table.loc[i,'html'] = ''

# Asynchronously scrape many urls, and store the results in the table
async def scrape_urls(urls, result_table):
    max_fetchers = settings.SCRAPER_NUM_CONNECTIONS

    tasks_to_rows = {}  # double as our list of currently active tasks
    num_urls = len(urls)
    started_urls = 0
    finished_urls = 0

    while finished_urls < num_urls:

        # start tasks until we max out connections, or run out of urls
        while ( len(tasks_to_rows) < max_fetchers ) and ( started_urls < num_urls ):
            newtask = event_loop.create_task(async_get_url(urls[started_urls]))
            tasks_to_rows[newtask] = started_urls
            started_urls += 1

        # Wait for any of the fetches to finish
        finished, pending = await asyncio.wait(tasks_to_rows.keys(), return_when=asyncio.FIRST_COMPLETED)

        # process any results we got
        for task in finished:
            try:
                response = task.result()
                add_result_to_table(result_table, tasks_to_rows[task], response)
            except asyncio.TimeoutError:
                add_timeout_to_table(result_table, tasks_to_rows[task])

            del tasks_to_rows[task]

        finished_urls += len(finished)





def render_urls(urlcol):
    pass



class URLScraper(ModuleImpl):

    @staticmethod
    def render(wf_module, table):
        return wf_module.retrieve_fetched_table()

    # Scrapy scrapy scrapy
    @staticmethod
    def event(wfm, event=None, **kwargs):

        # fetching could take a while so notify clients/users that we're working on it
        wfm.set_busy()

        urlcol = wfm.get_param_column('url')

        urls = render_urls(urlcol)

        out_table = pd.DataFrame({'urls': self.urls_small, 'status': ''}, columns=['urls', 'status', 'html'])

        event_loop.run_until_complete(scrapeurls(urls, out_table))

        save_fetched_table_if_changed(wfm, table, auto_change_version=auto)







