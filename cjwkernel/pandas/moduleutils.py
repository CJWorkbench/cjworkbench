from contextlib import contextmanager, asynccontextmanager
import io
import json
import re
from typing import Dict, Callable, Iterator, Optional
import aiohttp
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
import yarl  # aiohttp innards -- yuck!
from cjwkernel.util import tempfile_context
from cjwkernel.pandas.types import ProcessResult


_TextEncoding = Optional[str]
_ChunkSize = 1024 * 1024


class BadInput(ValueError):
    """
    Workbench cannot transform the given data into a pd.DataFrame.
    """


def uniquize_colnames(colnames: Iterator[str]) -> Iterator[str]:
    """
    Yield colnames in one pass, renaming so no two names are alike.

    The algorithm: Match each colname against "Column Name 2": everything up to
    ending digits is the 'key' and the ending digits are the 'number'. Maintain
    a blacklist of numbers, for each key; when a key+number have been seen,
    find the first _free_ number with that key to construct a new column name.

    This algorithm is ... generic. It's useful if we know nothing at all about
    the columns and no column names are "important" or "to-keep-unchanged".
    """
    blacklist = {}  # key => set of numbers
    regex = re.compile(r"\A(.*?) (\d+)\Z")
    for colname in colnames:
        # Find key and num
        match = regex.fullmatch(colname)
        if match:
            key = match.group(1)
            num = int(match.group(2))
        else:
            key = colname
            num = 1

        used_nums = blacklist.setdefault(key, set())
        if num in used_nums:
            num = max(used_nums) + 1
        used_nums.add(num)

        if not match and num == 1:
            # Common case: yield the original name
            yield key
        else:
            # Yield a unique name
            # The original colname had a number; the one we _output_ must also
            # have a number.
            yield key + " " + str(num)


def _safe_parse(
    bytesio: io.BytesIO, parser: Callable[[bytes], pd.DataFrame]
) -> ProcessResult:
    """
    Run the given parser, or return the error as a string.

    Empty dataset is not an error: it is just an empty dataset.
    """
    try:
        return ProcessResult.coerce(parser(bytesio))
    except BadInput as err:
        return ProcessResult(error=str(err))
    except json.decoder.JSONDecodeError as err:
        return ProcessResult(error=str(err))
    except pd.errors.EmptyDataError:
        return ProcessResult()
    except pd.errors.ParserError as err:
        return ProcessResult(error=str(err))


@contextmanager
def wrap_text(bytesio: io.BytesIO, text_encoding: _TextEncoding):
    """Yields the given BytesIO as a TextIO.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Encoding errors are converted to unicode replacement characters.
    """
    encoding = text_encoding or "utf-8"
    with io.TextIOWrapper(bytesio, encoding=encoding, errors="replace") as textio:
        yield textio


# Move dataframe column names into the first row of data, and replace column
# names with numbers. Used to undo first row of data incorrectly read as header
def turn_header_into_first_row(table: pd.DataFrame) -> pd.DataFrame:
    # Table may not be uploaded yet
    if table is None:
        return None

    new_line = pd.DataFrame([table.columns], columns=table.columns)
    new_table = pd.concat([new_line, table], ignore_index=True)

    new_table.columns = [str(i) for i in range(len(new_table.columns))]
    autocast_dtypes_in_place(new_table)

    # Convert 'object' columns to string. The prior instructions may have made
    # a column with all-numeric values except for row 0, which is a string.
    # Such a column will have type=object. We need to convert it to string.
    str_columns = new_table.select_dtypes(object)
    isna = str_columns.isna()
    new_table[str_columns.columns] = str_columns.astype(str)
    new_table[str_columns.columns][isna] = np.nan

    return new_table


@asynccontextmanager
async def spooled_data_from_url(
    url: str, headers: Dict[str, str] = {}, timeout: aiohttp.ClientTimeout = None
):
    """
    Download `url` to a tempfile and yield `(bytesio, headers, charset)`.

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
            async with session.get(url, headers=headers, timeout=timeout) as response:
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
