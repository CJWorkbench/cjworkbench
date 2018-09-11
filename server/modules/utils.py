import builtins
from collections import OrderedDict
from contextlib import contextmanager
import io
import json
from typing import Any, Dict, Callable, Optional
import xlrd
import pandas
from pandas import DataFrame
import pandas.errors
from .types import ProcessResult
import cchardet as chardet
from server.sanitizedataframe import autocast_dtypes_in_place
from django.conf import settings
from django.db.models.fields.files import FieldFile
from django.db import transaction
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from server.models.Workflow import Workflow
from .moduleimpl import ModuleImpl


_TextEncoding = Optional[str]


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
        return ProcessResult(dataframe=parser(bytesio, text_encoding))
    except json.decoder.JSONDecodeError as err:
        return ProcessResult(error=str(err))
    except xlrd.XLRDError as err:
        return ProcessResult(error=f'Error reading Excel file: {str(err)}')
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


def _parse_csv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """Build a DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    dtype = _determine_dtype(bytesio)
    with _wrap_text(bytesio, text_encoding) as textio:
        data = pandas.read_csv(textio, dtype=dtype)
        autocast_dtypes_in_place(data)
        return data


def _parse_tsv(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """Build a DataFrame or raise parse error.

    Peculiarities:

    * The file encoding defaults to UTF-8.
    * Data types. This is a CSV, so every value is a string ... _but_ we do the
      pandas default auto-detection.
    """
    dtype = _determine_dtype(bytesio)
    with _wrap_text(bytesio, text_encoding) as textio:
        data = pandas.read_table(textio, dtype=dtype)
        autocast_dtypes_in_place(data)
        return data


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
        data = json.load(textio, object_pairs_hook=OrderedDict)
        return pandas.DataFrame.from_records(data)


def _parse_xlsx(bytesio: io.BytesIO, _unused: _TextEncoding) -> DataFrame:
    """
    Build a DataFrame from xlsx bytes or raise parse error.

    Peculiarities:

    * Error can be xlrd.XLRDError or pandas error
    * We read the entire file contents into memory before parsing
    """
    dtype = _determine_dtype(bytesio)
    return pandas.read_excel(bytesio, dtype=dtype)

def _parse_txt(bytesio: io.BytesIO, text_encoding: _TextEncoding) -> DataFrame:
    """
        Build a DataFrame from txt bytes or raise parse error.

        Peculiarities:

        * The file encoding defaults to UTF-8.
        * Data types. Call _detect_separator to determine separator
    """
    dtype = _determine_dtype(bytesio)
    with _wrap_text(bytesio, text_encoding) as textio:
        sep = _detect_separator(textio)
        data = pandas.read_table(textio, dtype=dtype, sep=sep)
        autocast_dtypes_in_place(data)
        return data

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

    TODO: Could be a tie or no counts at all, keep going until you find a winner
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

def push_header(table: pandas.DataFrame) -> pandas.DataFrame:
    # Table may not be uploaded yet
    if type(table) == pandas.DataFrame:
        table.loc[-1] = table.columns
        table.columns = range(0, len(table.columns))
        table.index = table.index + 1
        return table.sort_index()
    else:
        return None

_parse_xls = _parse_xlsx


_Parsers = {
    'text/csv': _parse_csv,
    'text/tab-separated-values': _parse_tsv,
    'application/vnd.ms-excel': _parse_xls,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': _parse_xlsx,
    'application/json': _parse_json,
    'text/txt': _parse_txt
}


def parse_bytesio(bytesio: io.BytesIO, mime_type: str,
                  text_encoding: _TextEncoding=None) -> ProcessResult:
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
        parser = _Parsers[mime_type]
        if not text_encoding:
            text_encoding = _detect_encoding(bytesio)
        return _safe_parse(bytesio, parser, text_encoding)
    else:
        return ProcessResult(error=f'Unhandled MIME type "{mime_type}"')

# Utility functions for workflow import modules

def _get_wf_module_by_id(wf_id):
    try:
        with transaction.atomic():
            return Workflow.objects.select_for_update(nowait=False).get(id=wf_id)
    except Workflow.DoesNotExist:
        raise Exception('Target workflow does not exist')
    except Exception as e:
        raise e

def _validate_url(url):
    try:
        validate = URLValidator()
        validate(url)
    except ValidationError:
        return ValidationError('Invalid URL')

def get_id_from_url(url):
    #TODO: Environment check
    path = url.split('/')
    try:
        _validate_url(url)
        _id = int(path[path.index('workflows') + 1])
        return _id
    except ValueError:
        raise ValueError(f'Error fetching {url}: '
                'Invalid workflow URL')

def store_external_workflow(wf_module, url):
    right_wf_id = get_id_from_url(url)
    # fetching could take a while so notify clients/users we're working
    wf_module.set_busy()
    right_wf_module = _get_wf_module_by_id(right_wf_id)

    # Check to see if workflow_id the same
    if wf_module.workflow_id == right_wf_module.id:
        raise Exception('Cannot import the current workflow')

    # Make sure _this_ workflow's owner has access permissions to the _other_ workflow
    user = wf_module.workflow.owner
    if not right_wf_module.user_session_authorized_read(user, None):
        raise Exception('Access denied to the target workflow')

    right_wf_module = right_wf_module.wf_modules.last()

    # Always pull the cached result, so we can't execute() an infinite loop
    right_result = right_wf_module.get_cached_render_result().result
    result = ProcessResult(dataframe=right_result.dataframe)

    result.truncate_in_place_if_too_big()
    result.sanitize_in_place()
    ModuleImpl.commit_result(wf_module, result)
