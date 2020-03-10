import ssl
from contextlib import asynccontextmanager
from typing import Dict, Optional

import aiohttp
import pandas as pd
import yarl  # aiohttp innards -- yuck!
from cjwkernel.util import tempfile_context
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
