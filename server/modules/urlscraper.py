from .moduleimpl import ModuleImpl
from collections import OrderedDict
import pandas as pd
from pandas.io.common import CParserError
from xlrd import XLRDError
import io
import requests
import json
from server.versions import save_fetched_table_if_changed
from server.utils import sanitize_dataframe
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import aiohttp
import asyncio
import async_timeout

event_loop = asyncio.get_event_loop()

def is_valid_url(url):
    validate = URLValidator()
    try:
        validate(url)
        return True
    except ValidationError:
        return False

async def async_get_url(url, rownum):
        session = aiohttp.ClientSession()
        response = await session.get(url)
        return {'rownum':rownum, 'response':response}

# Parses the HTTP response object and stores it as a row in our table
def add_result_to_table(table, i, response):
    table.loc[i,'status'] = response['status']
    table.loc[i,'html'] = response['text']

async def scrapeurls(urls, result_table):
    max_fetchers = 8
    running_fetchers = []
    num_urls = len(urls)
    started_urls = 0
    finished_urls = 0

    while finished_urls < num_urls:

        while ( len(running_fetchers) < max_fetchers ) and ( started_urls<num_urls ):
            running_fetchers.append(
                event_loop.create_task(async_get_url(urls[started_urls], started_urls)))
            started_urls += 1

        # Wait for any of the fetches to finish
        finished, pending = await asyncio.wait(running_fetchers, return_when=asyncio.FIRST_COMPLETED)

        # process any results we got
        for task in finished:
            result = task.result()
            add_result_to_table(result_table, result['rownum'], result['response'])

        # keep waiting on unfinished tasks
        finished_urls += len(finished)
        running_fetchers = list(pending)




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

        # status=0 so NaNs don't turn this into a float cal
        out_table = pd.DataFrame({'urls': self.urls_small, 'status': 0}, columns=['urls', 'status', 'html'])

        event_loop.run_until_complete(scrapeurls(urls, out_table))

        save_fetched_table_if_changed(wfm, table, auto_change_version=auto)







