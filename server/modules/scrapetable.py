import asyncio
import aiohttp
import pandas as pd
from django.utils.translation import gettext as _
from .types import ProcessResult
from .moduleimpl import ModuleImpl
from server.modules import utils


def merge_colspan_headers_in_place(table) -> None:
    """
    Turn tuple colnames into strings.

    Pandas `read_html()` returns tuples for column names when scraping tables
    with colspan. Collapse duplicate entries and reformats to be human
    readable. E.g. ('year', 'year') -> 'year' and
    ('year', 'month') -> 'year - month'

    Alter the table in place, no return value.
    """

    newcols = []
    for c in table.columns:
        if isinstance(c, tuple):
            # collapse all runs of duplicate values:
            # 'a','a','b','c','c','c' -> 'a','b','c'
            vals = list(c)
            idx = 0
            while idx < len(vals) - 1:
                if vals[idx] == vals[idx + 1]:
                    vals.pop(idx)
                else:
                    idx += 1
            # put dashes between all remaining header values
            newcols.append(' - '.join(vals))
        else:
            newcols.append(c)
    table.columns = newcols


class ScrapeTable(ModuleImpl):
    @staticmethod
    def render(params, table, *, fetch_result, **kwargs):
        if not fetch_result:
            return table

        if fetch_result.status == 'error':
            return fetch_result

        table = fetch_result.dataframe

        has_header: bool = params['first_row_is_header']
        if has_header:
            table.columns = [str(c) for c in list(table.iloc[0, :])]
            table = table[1:]
            table.reset_index(drop=True, inplace=True)

        return (table, fetch_result.error)

    @staticmethod
    async def fetch(params, **kwargs):
        table = None
        url: str = params['url'].strip()
        tablenum: int = params['tablenum'] - 1  # 1-based for user

        if tablenum < 0:
            return ProcessResult(error='Table number must be at least 1')

        result = None

        try:
            async with utils.spooled_data_from_url(url) as (spool, headers,
                                                            charset):
                # TODO use charset for encoding detection
                tables = pd.read_html(spool, encoding=charset,
                                      flavor='html5lib')
        except asyncio.TimeoutError:
            return ProcessResult(error=f'Timeout fetching {url}')
        except aiohttp.InvalidURL:
            return ProcessResult(error=f'Invalid URL')
        except aiohttp.ClientResponseError as err:
            return ProcessResult(error=('Error from server: %d %s' % (
                                          err.status, err.message)))
        except aiohttp.ClientError as err:
            return ProcessResult(error=str(err))
        except ValueError as e:
            return ProcessResult(
                error=_('Did not find any <table> tags on that page')
            )
        except IndexError:
            # pandas.read_html() gives this unhelpful error message....
            return ProcessResult(error='Table has no columns')

        if not tables:
            return ProcessResult(
                error=_('Did not find any <table> tags on that page')
            )

        if tablenum >= len(tables):
            return ProcessResult(error=(
                f'The maximum table number on this page is {len(tables)}'
            ))

        table = tables[tablenum]
        merge_colspan_headers_in_place(table)
        result = ProcessResult(dataframe=table)
        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()
        return result
