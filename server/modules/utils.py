import builtins
from contextlib import contextmanager, asynccontextmanager
import io
import json
import re
import shutil
import tempfile
from typing import Any, Dict, Callable, Iterator, Optional
import aiohttp
import cchardet as chardet
from django.conf import settings
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype
import xlrd
import yarl  # aiohttp innards -- yuck!
from cjworkbench.types import ProcessResult


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


class PythonFeatureDisabledError(Exception):
    def __init__(self, name):
        super().__init__(self)
        self.name = name
        self.message = f"builtins.{name} is disabled"

    def __str__(self):
        return self.message


def build_builtins_for_eval() -> Dict[str, Any]:
    """
    Build a __builtins__ for use in custom code.

    Call ``exec(code, {'__builtins__': retval}, {})`` to use it.
    """
    # Start with _this_ module's __builtins__
    eval_builtins = dict(builtins.__dict__)

    # Disable "dangerous" builtins.
    #
    # This doesn't increase security: it just helps module authors.
    def disable_func(name):
        def _disabled(*args, **kwargs):
            raise PythonFeatureDisabledError(name)

        return _disabled

    to_disable = ["__import__", "breakpoint", "compile", "eval", "exec", "open"]
    for name in to_disable:
        eval_builtins[name] = disable_func(name)

    return eval_builtins


def build_globals_for_eval() -> Dict[str, Any]:
    """Builds a __globals__ for use in custom code.
    """
    eval_builtins = build_builtins_for_eval()

    # Hard-code modules we provide the user
    import math
    import pandas as pd
    import numpy as np

    return {"__builtins__": eval_builtins, "math": math, "np": np, "pd": pd}


def _safe_parse(
    bytesio: io.BytesIO,
    parser: Callable[[bytes], pd.DataFrame],
    text_encoding: _TextEncoding,
) -> ProcessResult:
    """Run the given parser, or return the error as a string.

    Empty dataset is not an error: it is just an empty dataset.
    """
    try:
        return ProcessResult.coerce(parser(bytesio, text_encoding))
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


def _parse_table(
    bytesio: io.BytesIO, sep: Optional[str], text_encoding: _TextEncoding
) -> pd.DataFrame:
    with wrap_text(bytesio, text_encoding) as textio:
        if not sep:
            sep = _detect_separator(textio)

        # Pandas CSV parser looks like this:
        #
        # 1. "Tokenize" the input stream: copy all its _data_ bytes into
        #    memory, and maintain arrays of "words" and "lines" pointers
        #    into that array.
        # 2. Determine list of columns
        # 3. Per-column, convert dtypes to array
        # 4. Smoosh arrays together into a pd.DataFrame.
        #
        # When `low_memory=True`, all this happens in a bigger loop, so
        # that the tokenized data structure is smaller.
        #
        # `low_memory=True` forces re-coding categories. That's `O(Ch * N
        # * Ca lg Ca)`, where Ch is number of column-chunks (9,000 * 60
        # in this case), N is number of records, Ch is number of chunks
        # (8, in this case), and Ca is the number of categories.
        #
        # This `rc11.txt` file has enormous `Ch`: 9,000 * 60 = 540,000.
        # `general.csv` (our 1.2GB file) is much smaller, at ~4,000, even
        # though it has 250x more rows. Pandas doesn't let us adjust
        # chunk size, and its heuristic is terrible for`rc11.txt`.
        #
        # Let's try `low_memory=False`. That makes the CPU cost
        # `O(N * Co * Ca lg Ca)`, where Co is the number of columns. Memory
        # usage grows by the number of cells. In the case of `general.csv`,
        # the cost is an extra 1GB.
        data = pd.read_csv(
            textio, dtype="category", sep=sep, na_filter=False, low_memory=False
        )
        data.reset_index(drop=True, inplace=True)  # empty => RangeIndex
        autocast_dtypes_in_place(data)
        return data


def _parse_csv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> pd.DataFrame:
    """Build a pd.DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    * For compatibility with EU CSVs we detect the separator
    """
    with wrap_text(bytesio, text_encoding) as textio:
        sep = _detect_separator(textio)
        return _parse_table(bytesio, sep, text_encoding)


def _parse_tsv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> pd.DataFrame:
    """Build a pd.DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    return _parse_table(bytesio, "\t", text_encoding)


def _parse_json(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> pd.DataFrame:
    """Build a pd.DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Pandas may auto-convert strings to dates/integers.
    * Columns are ordered as in the first JSON object, and the input must be an
      Array of Objects.
    * We may raise json.decoder.JSONDecodeError or pd.errors.ParserError.
    """
    with wrap_text(bytesio, text_encoding) as textio:
        try:
            data = pd.read_json(
                textio, orient="records", dtype=False, convert_dates=False
            )
        except ValueError as err:
            if "Mixing dicts with non-Series" in str(
                err
            ) or "If using all scalar values" in str(err):
                raise BadInput(
                    "Workbench cannot import this JSON file. The JSON file "
                    "must be an Array of Objects for Workbench to import it."
                )
            else:
                raise BadInput("Invalid JSON (%s)" % str(err))

        # pd.read_json(io.StringIO('{}')).colnames.index is a Float64Index for
        # some reason.
        #
        # There's no other reason to convert to str -- JSON keys are all str.
        if not len(data.columns):
            data.columns = data.columns.astype(str)

        # pd.read_json(io.StringIO('{}')) has a Float64Index instead of a
        # RangeIndex. No harm in setting RangeIndex always.
        data.reset_index(drop=True, inplace=True)

        # do not autocast_dtypes_in_place(): we want an str of ints to stay
        # str. But _do_ make sure all the types are valid.
        #
        # We allow str and numbers.
        colnames = [
            colname
            for colname, dtype in zip(data.columns, data.dtypes)
            if dtype == object
        ]
        strs = data[colnames].astype(str)
        strs[data[colnames].isna()] = np.nan
        data[colnames] = strs

        return data


def _parse_xlsx(bytesio: io.BytesIO, _unused: _TextEncoding) -> pd.DataFrame:
    """
    Build a pd.DataFrame from xlsx bytes or raise parse error.

    Peculiarities:

    * Error can be xlrd.XLRDError or pandas error
    * We read the entire file contents into memory before parsing
    """
    # dtype='category' crashes as of 2018-09-11
    try:
        # Use xlrd.open_workbook(): if we call pandas.read_excel(bytesio) it
        # will read the entire file into RAM.
        with tempfile.NamedTemporaryFile() as temp:
            shutil.copyfileobj(bytesio, temp)
            temp.flush()
            temp.seek(0)
            workbook = xlrd.open_workbook(temp.name)
            data = pd.read_excel(workbook, engine="xlrd", dtype=object)
    except xlrd.XLRDError as err:
        return ProcessResult(error=f"Error reading Excel file: {str(err)}")

    data.columns = [str(c) for c in data.columns]
    autocast_dtypes_in_place(data)
    return data


def _parse_txt(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> pd.DataFrame:
    """
    Build a pd.DataFrame from txt bytes or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. Call _detect_separator to determine separator
    """
    return _parse_table(bytesio, None, text_encoding)


def _detect_separator(textio: io.TextIOWrapper) -> str:
    """
    Detect most common char of '\t', ';', ',' in first MB

    TODO: Could be a tie or no counts at all, keep going until you find a
    winner.
    """
    map = [",", ";", "\t"]
    chunk = textio.read(settings.SEP_DETECT_CHUNK_SIZE)
    textio.seek(0)
    results = [chunk.count(x) for x in map]

    return map[results.index(max(results))]


def detect_encoding(bytesio: io.BytesIO):
    """
    Detect charset, as Python-friendly encoding string.

    Peculiarities:

    * Reads file by CHARDET_CHUNK_SIZE defined in settings.py
    * Stops seeking when detector.done flag True
    * Seeks back to beginning of file for downstream usage
    """
    detector = chardet.UniversalDetector()
    while not detector.done:
        chunk = bytesio.read(settings.CHARDET_CHUNK_SIZE)
        if not chunk:
            break  # EOF
        detector.feed(chunk)

    detector.close()
    bytesio.seek(0)
    return detector.result["encoding"]


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


_parse_xls = _parse_xlsx


_Parsers = {
    "text/csv": (_parse_csv, True),
    "text/tab-separated-values": (_parse_tsv, True),
    "application/vnd.ms-excel": (_parse_xls, False),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        _parse_xlsx,
        False,
    ),
    "application/json": (_parse_json, True),
    "text/plain": (_parse_txt, True),
}


def parse_bytesio(
    bytesio: io.BytesIO, mime_type: str, text_encoding: _TextEncoding = None
) -> ProcessResult:
    """Parse bytes to produce a ProcessResult.

    This will produce a _sane_ ProcessResult (see `types.validate_dataframe`).

    Keyword arguments:

    bytesio -- input bytes
    mime_type -- handled MIME type
    text_encoding -- if set and input is text-based, the suggested charset
                     (which may be incorrect)

    XXX See `upload` module for new-style parsers. New-style parsers operate on
    _files_, not _bytesio_; and they do not parse the first row as header.
    Basically, new-style parsers avoid all Pandas features.
    """
    if mime_type in _Parsers:
        parser, need_encoding = _Parsers[mime_type]
        if need_encoding and not text_encoding:
            text_encoding = detect_encoding(bytesio)
        return _safe_parse(bytesio, parser, text_encoding)
    else:
        return ProcessResult(error=f'Unhandled MIME type "{mime_type}"')


@asynccontextmanager
async def spooled_data_from_url(
    url: str, headers: Dict[str, str] = {}, timeout: aiohttp.ClientTimeout = None
):
    """
    Download `url` to a tempfile and yield `(bytesio, headers, charset)`.

    Raise aiohttp.ClientError on generic error. Subclasses of note:
    * aiohttp.InvalidURL on invalid URL
    * aiohttp.ClientResponseError when HTTP status is not 200

    Raise asyncio.TimeoutError when `timeout` seconds have expired.
    """

    # aiohttp internally performs URL canonization before sending
    # request. DISABLE THIS: it breaks oauth and user's expectations.
    #
    # https://github.com/aio-libs/aiohttp/issues/3424
    url = yarl.URL(url, encoded=True)  # prevent magic
    if url.scheme not in ("http", "https"):
        raise aiohttp.InvalidURL("URL must start with http:// or https://")

    with tempfile.TemporaryFile(prefix="loadurl") as spool:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=timeout, raise_for_status=True
            ) as response:
                response.raise_for_status()

                async for blob in response.content.iter_chunked(_ChunkSize):
                    spool.write(blob)

                headers = response.headers
                charset = response.charset

        spool.seek(0)
        yield spool, headers, charset


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
