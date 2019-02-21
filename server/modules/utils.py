import builtins
from collections import OrderedDict
from contextlib import contextmanager
import io
import json
import re
import shutil
import tempfile
from typing import Any, Dict, Callable, Optional
import aiohttp
from asgiref.sync import async_to_sync
from async_generator import asynccontextmanager  # TODO python 3.7 native
import cchardet as chardet
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.fields.files import FieldFile
from django.db import transaction
import numpy as np
import pandas
from pandas import DataFrame
import pandas.errors
import xlrd
import yarl  # aiohttp innards -- yuck!
from cjworkbench.types import ProcessResult
from server import rabbitmq
from server.models import Workflow
from server.sanitizedataframe import autocast_dtypes_in_place


_TextEncoding = Optional[str]
_ChunkSize = 1024 * 1024


class BadInput(ValueError):
    """
    Workbench cannot transform the given data into a DataFrame.
    """


def parse_multicolumn_param(value, table):
    """
    Get (valid_colnames, invalid_colnames) lists in `table`.

    It's easy for a user to select a missing column: just add a rename
    or column-select before the module that selected a valid column.

    Columns will be ordered as they are ordered in `table`.

    XXX this function is _weird_. By the time a module can call it, Workbench
    has _already_ nixed missing columns. So `invalid_colnames` will be empty
    unless `table` isn't the module's input table.
    """
    cols = value.split(',')
    cols = [c.strip() for c in cols if c.strip()]

    table_columns = list(table.columns)

    valid = [c for c in table.columns if c in cols]
    invalid = [c for c in cols if c not in table_columns]

    return (valid, invalid)


def parse_json_param(value) -> Dict[str, Any]:
    """
    Parse a JSON param.

    Sometimes, database values are already JSON. Other times, they're
    stored as ``str``. When given ``str``, we decode here (or raise
    ValueError on invalid JSON).

    TODO nix the duality. That way, users can store strings....
    """
    if isinstance(value, str):
        if value:
            return json.loads(value)  # raises ValueError
        else:
            # [2018-12-28] `None` seems more appropriate, but `{}` is
            # backwards-compatibile. TODO migrate database to nix this
            # ambiguity.
            return {}
    else:
        return value


class PythonFeatureDisabledError(Exception):
    def __init__(self, name):
        super().__init__(self)
        self.name = name
        self.message = f'builtins.{name} is disabled'

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
    to_disable = [
        '__import__',
        'breakpoint',
        'compile',
        'eval',
        'exec',
        'open',
    ]
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

    return {
        '__builtins__': eval_builtins,
        'math': math,
        'np': np,
        'pd': pd,
    }


def _safe_parse(bytesio: io.BytesIO, parser: Callable[[bytes], DataFrame],
                text_encoding: _TextEncoding) -> ProcessResult:
    """Run the given parser, or return the error as a string.

    Empty dataset is not an error: it is just an empty dataset.
    """
    try:
        return ProcessResult.coerce(parser(bytesio, text_encoding))
    except BadInput as err:
        return ProcessResult(error=str(err))
    except json.decoder.JSONDecodeError as err:
        return ProcessResult(error=str(err))
    except pandas.errors.EmptyDataError:
        return DataFrame()
    except pandas.errors.ParserError as err:
        return ProcessResult(error=str(err))


@contextmanager
def _wrap_text(bytesio: io.BytesIO, text_encoding: _TextEncoding):
    """Yields the given BytesIO as a TextIO.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Encoding errors are converted to unicode replacement characters.
    """
    encoding = text_encoding or 'utf-8'
    with io.TextIOWrapper(bytesio, encoding=encoding,
                          errors='replace') as textio:
        yield textio


def _parse_table(bytesio: io.BytesIO, sep: Optional[str],
                 text_encoding: _TextEncoding) -> DataFrame:
    with _wrap_text(bytesio, text_encoding) as textio:
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
        data = pandas.read_csv(textio, dtype='category', sep=sep,
                               na_filter=False, low_memory=False)

        autocast_dtypes_in_place(data)
        return data


def _parse_csv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """Build a DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    * For compatibility with EU CSVs we detect the separator
    """
    with _wrap_text(bytesio, text_encoding) as textio:
        sep = _detect_separator(textio)
        return _parse_table(bytesio, sep, text_encoding)


def _parse_tsv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """Build a DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    return _parse_table(bytesio, '\t', text_encoding)


def _parse_json(bytesio: io.BytesIO,
                text_encoding: _TextEncoding) -> DataFrame:
    """Build a DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Pandas may auto-convert strings to dates/integers.
    * Columns are ordered as in the first JSON object, and the input must be an
      Array of Objects.
    * We may raise json.decoder.JSONDecodeError or pandas.errors.ParserError.
    """
    with _wrap_text(bytesio, text_encoding) as textio:
        try:
            data = pandas.read_json(textio, orient='records', dtype=False,
                                    convert_dates=False)
        except ValueError as err:
            if 'Mixing dicts with non-Series' in str(err):
                raise BadInput(
                    'Workbench cannot import this JSON file. The JSON file '
                    'must be an Array of Objects for Workbench to import it.'
                )
            else:
                raise BadInput('Invalid JSON (%s)' % str(err))

        # do not autocast_dtypes_in_place(): we want an str of ints to stay
        # str. But _do_ make sure all the types are valid.
        #
        # We allow str and numbers.
        colnames = [colname
                    for colname, dtype in zip(data.columns, data.dtypes)
                    if dtype == object]
        strs = data[colnames].astype(str)
        strs[data[colnames].isna()] = np.nan
        data[colnames] = strs

        return data


def _parse_xlsx(bytesio: io.BytesIO, _unused: _TextEncoding) -> DataFrame:
    """
    Build a DataFrame from xlsx bytes or raise parse error.

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
            data = pandas.read_excel(workbook, engine='xlrd', dtype=object)
    except xlrd.XLRDError as err:
        return ProcessResult(error=f'Error reading Excel file: {str(err)}')

    autocast_dtypes_in_place(data)
    return data


def _parse_txt(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """
    Build a DataFrame from txt bytes or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. Call _detect_separator to determine separator
    """
    return _parse_table(bytesio, None, text_encoding)


def _determine_dtype(bytesio: io.BytesIO):
    """
    Either improve read performance time or save memory depending on file size

    Peculiarities:

    * Unittests pass bytesio as io.BytesIO
    * Django passes as FieldFile.
    * Both have different methods to determine buffer size
    """

    if type(bytesio) == FieldFile:
        size = bytesio.size
    elif type(bytesio) == io.BytesIO:
        size = bytesio.getbuffer().nbytes
    else:
        return None

    if size > settings.CATEGORY_FILE_SIZE_MIN:
        return 'category'
    else:
        return None


def _detect_separator(textio: io.TextIOWrapper) -> str:
    """
    Detect most common char of '\t', ';', ',' in first MB

    TODO: Could be a tie or no counts at all, keep going until you find a
    winner.
    """
    map = [',', ';', '\t']
    chunk = textio.read(settings.SEP_DETECT_CHUNK_SIZE)
    textio.seek(0)
    results = [chunk.count(x) for x in map]

    return map[results.index(max(results))]


def _detect_encoding(bytesio: io.BytesIO):
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
    return detector.result['encoding']


# Move dataframe column names into the first row of data, and replace column
# names with numbers. Used to undo first row of data incorrectly read as header
def turn_header_into_first_row(table: pandas.DataFrame) -> pandas.DataFrame:
    # Table may not be uploaded yet
    if table is None:
        return None

    new_line = DataFrame([table.columns], columns=table.columns)
    new_table = pandas.concat([new_line, table], ignore_index=True)

    new_table.columns = [str(i) for i in range(len(new_table.columns))]
    autocast_dtypes_in_place(new_table)

    return new_table


_parse_xls = _parse_xlsx


_Parsers = {
    'text/csv': (_parse_csv, True),
    'text/tab-separated-values': (_parse_tsv, True),
    'application/vnd.ms-excel': (_parse_xls, False),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        (_parse_xlsx, False),
    'application/json': (_parse_json, True),
    'text/plain': (_parse_txt, True),
}


def parse_bytesio(bytesio: io.BytesIO, mime_type: str,
                  text_encoding: _TextEncoding = None) -> ProcessResult:
    """Parse bytes to produce a ProcessResult.

    You should call .sanitize_in_place() on the result: otherwise there may be
    nested objects in the result (from parsing nested JSON).

    Keyword arguments:

    bytesio -- input bytes
    mime_type -- handled MIME type
    text_encoding -- if set and input is text-based, the suggested charset
                     (which may be incorrect)
    """
    if mime_type in _Parsers:
        parser, need_encoding = _Parsers[mime_type]
        if need_encoding and not text_encoding:
            text_encoding = _detect_encoding(bytesio)
        return _safe_parse(bytesio, parser, text_encoding)
    else:
        return ProcessResult(error=f'Unhandled MIME type "{mime_type}"')


_WORKFLOW_REGEX = re.compile(
    r'^\s*(?:https?://)?[-_a-z0-9A-Z.]+/workflows/(\d+)/?\s*$'
)


def workflow_url_to_id(url):
    """
    Turn a URL into a Workflow ID.

    Raise ValueError if it is not a valid Workflow ID.
    """
    match = _WORKFLOW_REGEX.match(url)
    if not match:
        raise ValueError('Not a valid Workbench workflow URL')

    return int(match.group(1))


@database_sync_to_async
def fetch_external_workflow(calling_workflow_id: int,
                            workflow_owner: User,
                            other_workflow_id: int) -> ProcessResult:
    """
    Lookup up a workflow's final ProcessResult.

    `calling_workflow_id` is to raise an error if we try to import ourselves.

    `calling_workflow_owner` is to give access to non-public workflows if we
    have permission.
    """
    if calling_workflow_id == other_workflow_id:
        return ProcessResult(error='Cannot import the current workflow')

    with transaction.atomic():
        # Mimic cooperative_lock() on right_workflow, with less overhead. It's
        # transaction.atomic() and select_for_update().
        try:
            other_workflow = Workflow.objects \
                .select_for_update() \
                .get(id=other_workflow_id)
        except Workflow.DoesNotExist:
            return ProcessResult(error='Target workflow does not exist')

        # Make sure _this_ workflow's owner has access permissions to the
        # _other_ workflow
        if not other_workflow.user_session_authorized_read(workflow_owner,
                                                           None):
            return ProcessResult(error='Access denied to the target workflow')

        other_wf_module = other_workflow \
            .live_tabs.first() \
            .live_wf_modules.last()
        if other_wf_module is None:
            return ProcessResult(error='Target workflow is empty')

        # Always pull the cached result, so we can't execute() an infinite loop
        crr = other_wf_module.cached_render_result

        if not crr:
            # Workflow has not been rendered completely. This is either because
            # a render is queued/running, or because a render was never queued.
            # (e.g., when cron fetches a new version, no render is queued.)
            # Queue a render and tell the user to try again. If the render is
            # spurious, that isn't a big deal.
            async_to_sync(rabbitmq.queue_render)(other_workflow.id,
                                                 other_workflow.last_delta_id)
            return ProcessResult(
                error='Target workflow is rendering. Please try again.'
            )

        result = crr.result

    return ProcessResult(dataframe=result.dataframe)


@asynccontextmanager
async def spooled_data_from_url(url: str, headers: Dict[str, str] = {},
                                timeout: aiohttp.ClientTimeout = None):
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
    if url.scheme not in ('http', 'https'):
        raise aiohttp.InvalidURL('URL must start with http:// or https://')

    with tempfile.TemporaryFile(prefix='loadurl') as spool:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers,
                                   timeout=timeout,
                                   raise_for_status=True) as response:
                response.raise_for_status()

                async for blob in response.content.iter_chunked(_ChunkSize):
                    spool.write(blob)

                headers = response.headers
                charset = response.charset

        spool.seek(0)
        yield spool, headers, charset
