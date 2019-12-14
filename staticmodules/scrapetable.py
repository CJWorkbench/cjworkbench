import asyncio
import aiohttp
from contextlib import contextmanager
import io
from typing import Optional
import pandas as pd
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.pandas import moduleutils


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
            newcols.append(" - ".join(vals))
        elif isinstance(c, int):
            # If first row isn't header and there's no <thead>, table.columns
            # will be an integer index.
            newcols.append("Column %d" % (c + 1))
        else:
            newcols.append(c)
    # newcols can contain duplicates. Rename them.
    table.columns = list(moduleutils.uniquize_colnames(newcols))


def render(table, params, *, fetch_result):
    if not fetch_result:
        return table

    if fetch_result.status == "error":
        return fetch_result

    table = fetch_result.dataframe

    has_header: bool = params["first_row_is_header"]
    if has_header and len(table) >= 1:  # if len == 0, no-op
        table.columns = list(
            moduleutils.uniquize_colnames(
                str(c) or ("Column %d" % (i + 1))
                for i, c in enumerate(table.iloc[0, :])
            )
        )
        table.drop(index=0, inplace=True)
        table.reset_index(drop=True, inplace=True)
        moduleutils.autocast_dtypes_in_place(table)

    if fetch_result.error:
        return (table, fetch_result.error)
    else:
        return table


@contextmanager
def wrap_text(bytesio: io.BytesIO, text_encoding: Optional[str]):
    """Yields the given BytesIO as a TextIO.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Encoding errors are converted to unicode replacement characters.
    """
    encoding = text_encoding or "utf-8"
    with io.TextIOWrapper(bytesio, encoding=encoding, errors="replace") as textio:
        yield textio


async def fetch(params):
    # We delve into pd.read_html()'s innards, below. Part of that means some
    # first-use initialization.
    pd.io.html._importers()

    table = None
    url: str = params["url"].strip()
    tablenum: int = params["tablenum"] - 1  # 1-based for user

    if tablenum < 0:
        return ProcessResult.coerce("Table number must be at least 1")

    result = None

    try:
        async with moduleutils.spooled_data_from_url(url) as (spool, headers, charset):
            # pandas.read_html() does automatic type conversion, but we prefer
            # our own. Delve into its innards so we can pass all the conversion
            # kwargs we want.
            with wrap_text(spool, charset) as textio:
                tables = pd.io.html._parse(
                    # Positional arguments:
                    flavor="html5lib",  # force algorithm, for reproducibility
                    io=textio,
                    match=".+",
                    attrs=None,
                    encoding=None,  # textio is already decoded
                    displayed_only=False,  # avoid dud feature: it ignores CSS
                    # Required kwargs that pd.read_html() would set by default:
                    header=None,
                    skiprows=None,
                    # Now the reason we used pd.io.html._parse() instead of
                    # pd.read_html(): we get to pass whatever kwargs we want to
                    # TextParser.
                    #
                    # kwargs we get to add as a result of this hack:
                    na_filter=False,  # do not autoconvert
                    dtype=str,  # do not autoconvert
                )
    except asyncio.TimeoutError:
        return ProcessResult.coerce("Timeout fetching {url}")
    except aiohttp.InvalidURL:
        return ProcessResult.coerce("Invalid URL")
    except aiohttp.ClientResponseError as err:
        return ProcessResult.coerce(
            "Error from server: %d %s" % (err.status, err.message)
        )
    except aiohttp.ClientError as err:
        return ProcessResult.coerce(str(err))
    except ValueError:
        return ProcessResult.coerce("Did not find any <table> tags on that page")
    except IndexError:
        # pandas.read_html() gives this unhelpful error message....
        return ProcessResult.coerce("Table has no columns")

    if not tables:
        return ProcessResult.coerce("Did not find any <table> tags on that page")

    if tablenum >= len(tables):
        return ProcessResult.coerce(
            f"The maximum table number on this page is {len(tables)}"
        )

    # pd.read_html() guarantees unique colnames
    table = tables[tablenum]
    merge_colspan_headers_in_place(table)
    moduleutils.autocast_dtypes_in_place(table)
    if len(table) == 0:
        # read_html() produces an empty Index. We want a RangeIndex.
        table.reset_index(drop=True, inplace=True)
    result = ProcessResult(dataframe=table)
    result.truncate_in_place_if_too_big()
    return result
