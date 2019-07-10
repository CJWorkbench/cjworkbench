import aiohttp
import asyncio
import re
from django.conf import settings
from django.utils import timezone
import pandas as pd
import yarl  # aiohttp innards -- yuck!
from cjworkbench.types import ProcessResult


MaxNUrls = 10


async def async_get_url(row, url):
    """
    Return a Future (row, status, text).

    The Future will resolve within settings.SCRAPER_TIMEOUT seconds. `status`
    may be '

    The Future will resolve within settings.SCRAPER_TIMEOUT seconds. The
    exception may be `asyncio.TimeoutError`, `ValueError` (invalid URL) or
    `aiohttp.client_exceptions.ClientError`.
    """
    session = aiohttp.ClientSession()

    try:
        # aiohttp internally performs URL canonization before sending
        # request. DISABLE THIS: it breaks oauth and user's expectations.
        #
        # https://github.com/aio-libs/aiohttp/issues/3424
        url = yarl.URL(url, encoded=True)  # prevent magic

        response = await session.get(url, timeout=settings.SCRAPER_TIMEOUT)
        # We have the header. Now read the content.
        # response.text() times out according to SCRAPER_TIMEOUT above. See
        # https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
        text = await response.text()

        return (row, str(response.status), text)
    except asyncio.TimeoutError:
        return (row, "Timed out", "")
    except aiohttp.InvalidURL:
        return (row, "Invalid URL", "")
    except aiohttp.ClientError as err:
        return (row, f"Can't connect: {err}", "")
    except asyncio.CancelledError as err:
        raise
    except Exception as err:
        return (row, f"Unknown error: {err}", "")


# Asynchronously scrape many urls, and store the results in the table
async def scrape_urls(urls, result_table):
    next_queued_row = 0  # index into urls
    fetching = set()  # {Future<response>}

    max_fetchers = settings.SCRAPER_NUM_CONNECTIONS

    while next_queued_row < len(urls) or fetching:
        # start tasks until we max out connections, or run out of urls
        while next_queued_row < len(urls) and len(fetching) < max_fetchers:
            row = next_queued_row
            url = urls[row].strip()
            fetching.add(async_get_url(row, url))

            next_queued_row += 1

        assert fetching

        # finish one or more tasks, then loop
        done, pending = await asyncio.wait(
            fetching, return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            row, status, text = await task
            result_table.loc[row, "status"] = status
            result_table.loc[row, "html"] = text

        fetching = pending  # delete done tasks


def are_params_empty(params, input_table):
    urlsource: int = params["urlsource"]
    if urlsource == "list":
        urllist: str = params["urllist"]
        return not urllist
    elif urlsource == "column":
        urlcol: str = params["urlcol"]
        return urlcol is None
    else:  # urlsource == 'paged'
        return not params["pagedurl"]


def render(table, params, *, fetch_result):
    # TODO nix this method? It looks like the default implementation should do.
    if are_params_empty(params, table):
        return table

    if fetch_result is None:
        return table

    else:
        return fetch_result


async def fetch(params, *, get_input_dataframe):
    urls = []
    urlsource = params["urlsource"]
    error = ""

    if urlsource == "list":
        if are_params_empty(params, None):
            return None
        urllist_text: str = params["urllist"]
        urllist_raw = urllist_text.split("\n")
        for url in urllist_raw:
            s_url = url.strip()
            if len(s_url) == 0:
                continue
            # Fix in case user adds an URL without http(s) prefix
            if not re.match("^https?://.*", s_url):
                urls.append("http://{}".format(s_url))
            else:
                urls.append(s_url)
        if not urls:
            return None
    elif urlsource == "column":
        # We won't execute here -- there's no need: the user clicked a
        # button so should be pretty clear on what the input is.
        prev_table = await get_input_dataframe()
        if prev_table is None:
            prev_table = pd.DataFrame()

        if are_params_empty(params, prev_table):
            return None

        # get our list of URLs from a column in the input table
        urlcol: str = params["urlcol"]
        urls = prev_table[urlcol].tolist()
    elif urlsource == "paged":
        # Count through a list of page numbers, appending each to the URL
        if are_params_empty(params, None):
            return None

        pagedurl: str = params["pagedurl"]
        # Fix in case user adds an URL without http(s) prefix
        if not re.match("^https?://.*", pagedurl):
            pagedurl = "http://" + pagedurl

        begin = params["startpage"]
        end = params["endpage"] + 1
        if end - begin > MaxNUrls:
            end = begin + MaxNUrls
            error = f"We limited your scrape to {MaxNUrls} URLs"

        # Generate multiple urls by adding page numbers, if user says so
        if params["addpagenumbers"]:
            # limit the number of pages we can scrape with this method
            urls = [pagedurl + str(num) for num in range(begin, end)]
        else:
            urls = [pagedurl]
    else:
        raise RuntimeError("Invalid urlsource")

    if len(urls) > MaxNUrls:
        urls = urls[:MaxNUrls]
        error = f"We limited your scrape to {MaxNUrls} URLs"

    table = pd.DataFrame(
        {
            "url": urls,
            # TODO use response date, not current date
            "date": (
                timezone.now().isoformat(timespec="seconds").replace("+00:00", "Z")
            ),
            "status": "",
            "html": "",
        }
    )

    await scrape_urls(urls, table)
    if error:
        return table, error
    else:
        return table


def _migrate_params_v0_to_v1(params):
    """
    v0: urlsource was 0 ("List") or 1 ("Input column")

    v1: urlsource is "list" or "column".
    """
    return {**params, "urlsource": ["list", "column"][params["urlsource"]]}


def _migrate_params_v1_to_v2(params):
    """
    v2 adds "paged" option to urlsource menu and related parameters
    """
    return {
        **params,
        "pagedurl": "",
        "addpagenumbers": False,  # defaults, from json file
        "startpage": 0,
        "endpage": 9,
    }


def _migrate_params_v2_to_v3(params):
    """
    v3 adds "addpagenumbers" checkbox
    """
    return {**params, "addpagenumbers": True}  # match v2 behavior


def migrate_params(params):
    if isinstance(params["urlsource"], int):
        params = _migrate_params_v0_to_v1(params)
    if "pagedurl" not in params:
        params = _migrate_params_v1_to_v2(params)
    if "addpagenumbers" not in params:
        params = _migrate_params_v2_to_v3(params)
    return params
