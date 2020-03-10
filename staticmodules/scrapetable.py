import asyncio
import io
import ssl
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from typing import Dict, Optional

import aiohttp
import pandas as pd
import yarl  # aiohttp innards -- yuck!
from cjwkernel.pandas.types import ProcessResult
from cjwkernel.util import tempfile_context
from cjwmodule.util.colnames import gen_unique_clean_colnames
from pandas.api.types import is_datetime64_dtype, is_numeric_dtype

_ChunkSize = 1024 * 1024


@asynccontextmanager
async def spooled_data_from_url(
    url: str,
    headers: Dict[str, str] = {},
    timeout: aiohttp.ClientTimeout = None,
    *,
    ssl: Optional[ssl.SSLContext] = None,
):
    """
    Download `url` to a tempfile and yield `(bytesio, headers, charset)`.

    `bytesio` is backed by a temporary file: the file at path `bytesio.name`
    will exist within this context.

    Raise aiohttp.ClientError on generic error. Subclasses of note:
    * aiohttp.InvalidURL on invalid URL
    * aiohttp.ClientResponseError when HTTP status is not 200
    * aiohttp.ClientPayloadError when server closes connection prematurely
    * aiohttp.ClientConnectionError (OSError) when connection fails

    Raise asyncio.TimeoutError when `timeout` seconds have expired.
    """

    # aiohttp internally performs URL canonization before sending
    # request. DISABLE THIS: it breaks oauth and user's expectations.
    #
    # https://github.com/aio-libs/aiohttp/issues/3424
    url = yarl.URL(url, encoded=True)  # prevent magic
    if url.scheme not in ("http", "https"):
        raise aiohttp.InvalidURL("URL must start with http:// or https://")

    with tempfile_context(prefix="loadurl") as spool_path:
        async with aiohttp.ClientSession() as session:
            # raise aiohttp.ClientError, asyncio.TimeoutError
            async with session.get(
                url, headers=headers, timeout=timeout, ssl=ssl
            ) as response:
                # raise aiohttp.ClientResponseError
                response.raise_for_status()
                headers = response.headers
                charset = response.charset

                with spool_path.open("wb") as spool:
                    # raise aiohttp.ClientPayloadError
                    async for blob in response.content.iter_chunked(_ChunkSize):
                        spool.write(blob)

        yield spool_path.open("rb"), headers, charset


# dependency-injection, so unit tests can mock our functions
di = SimpleNamespace(spooled_data_from_url=spooled_data_from_url)


def autocast_series_dtype(series: pd.Series) -> pd.Series:
    """
    Cast any sane Series to str/category[str]/number/datetime.

    This is appropriate when parsing CSV data or Excel data. It _seems_
    appropriate when a search-and-replace produces numeric columns like
    '$1.32' => '1.32' ... but perhaps that's only appropriate in very-specific
    cases.

    The input must be "sane": if the dtype is object or category, se assume
    _every value_ is str (or null).

    If the series is all-null, do nothing.

    Avoid spurious calls to this function: it's expensive.

    TODO handle dates and maybe booleans.
    """
    if series.dtype == object:
        nulls = series.isnull()
        if (nulls | (series == "")).all():
            return series
        try:
            # If it all looks like numbers (like in a CSV), cast to number.
            return pd.to_numeric(series)
        except (ValueError, TypeError):
            # Otherwise, we want all-string. Is that what we already have?
            #
            # TODO assert that we already have all-string, and nix this
            # spurious conversion.
            array = series[~nulls].array
            if any(type(x) != str for x in array):
                series = series.astype(str)
                series[nulls] = None
            return series
    elif hasattr(series, "cat"):
        # Categorical series. Try to infer type of series.
        #
        # Assume categories are all str: after all, we're assuming the input is
        # "sane" and "sane" means only str categories are valid.
        if (series.isnull() | (series == "")).all():
            return series
        try:
            return pd.to_numeric(series)
        except (ValueError, TypeError):
            # We don't cast categories to str here -- because we have no
            # callers that would create categories that aren't all-str. If we
            # ever do, this is where we should do the casting.
            return series
    else:
        assert is_numeric_dtype(series) or is_datetime64_dtype(series)
        return series


def autocast_dtypes_in_place(table: pd.DataFrame) -> None:
    """
    Cast str/object columns to numeric, if possible.

    This is appropriate when parsing CSV data, or maybe Excel data. It is
    probably not appropriate to call this method elsewhere, since it destroys
    data types all over the table.

    The input must be _sane_ data only!

    TODO handle dates and maybe booleans.
    """
    for colname in table:
        column = table[colname]
        table[colname] = autocast_series_dtype(column)


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
    table.columns = [c.name for c in gen_unique_clean_colnames(newcols)]


def render(table, params, *, fetch_result):
    if not fetch_result:
        return table

    if fetch_result.status == "error":
        return fetch_result

    table = fetch_result.dataframe

    has_header: bool = params["first_row_is_header"]
    if has_header and len(table) >= 1:  # if len == 0, no-op
        # TODO inform user of column-rename warnings
        table.columns = [
            uccn.name
            for uccn in gen_unique_clean_colnames([str(c) for c in table.iloc[0, :]])
        ]
        table.drop(index=0, inplace=True)
        table.reset_index(drop=True, inplace=True)
        autocast_dtypes_in_place(table)

    if fetch_result.errors:
        return (table, fetch_result.errors)
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
        async with di.spooled_data_from_url(url) as (spool, headers, charset):
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
    autocast_dtypes_in_place(table)
    if len(table) == 0:
        # read_html() produces an empty Index. We want a RangeIndex.
        table.reset_index(drop=True, inplace=True)
    result = ProcessResult(dataframe=table)
    result.truncate_in_place_if_too_big()
    return result
