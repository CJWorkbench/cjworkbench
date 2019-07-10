import codecs
from contextlib import contextmanager
import csv
import datetime
from dataclasses import dataclass
from enum import Enum
import io
import json
import math
import pathlib
import sys
from yajl import YajlParser, YajlContentHandler, YajlError
from typing import Dict, List, Optional, Tuple, Union
from django.conf import settings
import pandas as pd
from .utils import (
    detect_encoding,
    wrap_text,
    uniquize_colnames,
    autocast_series_dtype,
    turn_header_into_first_row,
    parse_bytesio as bad_parse_bytesio,
)


CellValue = Union[int, float, str, datetime.datetime]


def _utf8(b: bytes) -> str:
    """Parse bytes we already know are utf-8."""
    return codecs.utf_8_decode(b, None, True)[0]


class ColumnBuilder:
    """
    Compact accumulator of values for a column.

    It can hold number, text and datetime values. Strings are treated specially.

    Similarities to pandas read_csv:

    * Like the Pandas C engine, we "intern" strings: if the same string appears
      twice, both instances use the same Python Object. This costs an extra few
      bytes per string (to fill a hash table); it saves 50 bytes per dup.

    Differences:

    * We store each column in a separate buffer. This lets us read
      variable-length rows: storing data per-column means we can fill in NA
      when we come up against a new column. (Pandas can't do this.)
    * Our NA logic is different. First off, we don't use Pandas' `na_filter`
      stuff. That means "na" only comes up in one case: this column doesn't
      have a value in every row. We write "-1" to our buffer in that case.
      ("0" means, "empty string.")
    * We do not cast. (Casting comes after parsing.)
    * We aren't like the Pandas C engine: we parse text, not bytes. (Pandas
      C engine re-encodes the entire file to UTF-8 before parsing.)
    * We aren't C-optimized (yet).
    """

    def __init__(self):
        self._intern = {}  # hash of str to itself
        self.n_bytes = 0
        self.n_values = 0  # number of non-NA values
        self.value_types = set()
        self.values: List[Optional[CellValue]] = []

    def feed(self, row: int, value: Optional[CellValue]):
        """
        Feed a new value.

        If `row` is greater than `len(self.values)`, fill in `None` 

        Return number of bytes we're costing.
        """
        if value is not None:
            self.value_types.add(type(value))
        if isinstance(value, str):
            input_value = value
            value = self._intern.setdefault(input_value, input_value)
            interned = value is not input_value
        else:
            interned = False

        n_na_to_prepend = row - len(self.values)

        for _ in range(n_na_to_prepend):
            self.values.append(None)
        self.values.append(value)
        self.n_values += 1

        return (
            n_na_to_prepend * 8  # newly-added NA values
            + 8  # pointer in self.values
            + 8  # hash-table entry
            + (0 if interned else sys.getsizeof(value))
        )

    @property
    def should_store_as_categorical(self):
        """
        True if a "categorical" dtype would save enough RAM to be worthwhile.

        In the worst case, a "categorical" column can have an enormous data
        dictionary and no savings. (This is the case for, say, HTML scraped
        from a website.) In the best case, a "categorical" column has a small
        dictionary and stores oodles of info in a tiny data structure. We use
        wishy-washy heuristics to decide which case we're in.
        """
        if self.value_types != set([str]):
            # all-NA or mixed-type inputs aren't categorical
            return False

        n_unique = len(self._intern)

        # for now, magic number: "categorical is <80% the size of list"
        return n_unique / self.n_values < 0.8


@dataclass
class ParseTableResult:
    columns: List[ColumnBuilder]
    error: str


@dataclass
class ParseJsonResult:
    columns: Dict[str, ColumnBuilder]
    error: str


def parse_table(textio: io.TextIOBase, dialect: csv.Dialect) -> ParseTableResult:
    """
    Convert CSV to List[ColumnBuilder].

    Rules:

    * Column names are 'Column 1', 'Column 2', etc.
    * All values are str.
    * We drop every row starting at MAX_BYTES_PER_TABLE (and warn).
    * We drop every column after MAX_COLUMNS_PER_TABLE (and warn).
    * We drop every row after MAX_ROWS_PER_TABLE (and warn).
    """
    columns: List[ColumnBuilder] = []  # column-wise data
    MAX_COLUMNS = settings.MAX_COLUMNS_PER_TABLE
    MAX_ROWS = settings.MAX_ROWS_PER_TABLE
    MAX_BYTES = settings.MAX_BYTES_PER_TABLE

    n_bytes = 0
    n_input_rows = 0
    n_input_columns = None  # only set if we exceed MAX_COLUMNS

    csv_reader = csv.reader(textio, dialect)
    for values in csv_reader:
        # simulate Pandas "skip empty rows"
        if not values:
            continue

        row = n_input_rows
        n_input_rows += 1
        if n_input_rows > MAX_ROWS or n_bytes > MAX_BYTES:
            # keep CSV-parsing, to complete n_input_rows so we can set a
            # good truncation message. But ignores all values.
            continue

        for i, value in enumerate(values):
            if n_bytes > MAX_BYTES:
                break

            if i >= len(columns):
                if i >= MAX_COLUMNS:  # nested within the other if-statement
                    n_input_columns = max(n_input_columns or 0, len(values))
                    break  # we'll warn -- n_columns is set

                # Add new column
                column = ColumnBuilder()
                columns.append(column)
            else:
                column = columns[i]
            n_bytes += column.feed(row, value)

    warnings = []
    if n_bytes > MAX_BYTES or n_input_rows > MAX_ROWS:
        warnings.append(
            "The input was too large, so we removed %d rows"
            % (n_input_rows - len(columns[0].values))
        )
    if n_input_columns is not None:
        warnings.append(
            "The input had too many columns, so we removed %d columns"
            % (n_input_columns - MAX_COLUMNS)
        )

    return ParseTableResult(columns, "\n".join(warnings))


def _csv_columns_to_dataframe_destructive(
    columns: List[ColumnBuilder], has_header: bool
) -> pd.DataFrame:
    """
    Empty a List[ColumnBuilder] to build a pd.DataFrame.

    Why are we destructive (deleting the input list)? Because it saves RAM
    (assuming we don't hold other handles to this list's ColumnBuilders).

    Logic:

    * Column names default to 'Column 1', 'Column 2', etc; they are overridden
      by the first row if has_header=True for every non-NA value in the first
      row.
    * Values are converted to numbers if they are all numeric.
    * Otherwise, they're converted to category if we expect a space savings.
    """
    # column names:
    # * If has_header, pick name from row 0 (which is guaranteed to exist for
    #   each column)
    # * Default to 'Column 1', 'Column 2', etc. (if header is '' or None.)
    # * Use naive uniquize algorithm.
    colnames = list(
        uniquize_colnames(
            c.values[0] if has_header and c.values[0] else f"Column {i + 1}"
            for i, c in enumerate(columns)
        )
    )

    for i, colname in enumerate(colnames):
        column = columns[i]
        values = column.values
        if has_header:
            values = values[1:]
        series = autocast_series_dtype(pd.Series(values, name=colname))
        if series.dtype == object and column.should_store_as_categorical:
            series = series.astype("category")
        # modify `columns` in-place: frees RAM `columns[i]` RAM
        columns[i] = series

    return pd.DataFrame({s.name: s for s in columns})


class JsonValidationError(ValueError):
    pass


class JsonRootIsNotArray(JsonValidationError):
    pass


class JsonRecordIsNotObject(JsonValidationError):
    pass


class JsonTooManyRows(JsonValidationError):
    pass


class JsonTooManyBytes(JsonValidationError):
    pass


class JsonNumberTooLarge(JsonValidationError):
    def __init__(self, value_str: str):
        super().__init__()
        self.value_str = value_str


class JsonContentHandler(YajlContentHandler):
    def __init__(self):
        self.in_root_array = False
        self.in_record = False
        self.columns: Dict[str, ColumnBuilder] = {}
        # self.column is None if not self.in_record or if we hit column limit
        self.column: Optional[ColumnBuilder] = None

        # value_stack is non-empty stack of JSON-serialized Array/Objects
        # If in array, top of stack is JSON-serialized values
        # If in object, top of stack is flattened pairs of key and
        # JSON-serialized value
        self.value_stack: List[List[str]] = []
        self.row = 0
        self.n_bytes = 0
        self.max_rows = settings.MAX_ROWS_PER_TABLE
        self.max_cols = settings.MAX_COLUMNS_PER_TABLE
        self.max_bytes = settings.MAX_BYTES_PER_TABLE
        self.truncated_columns = False

    def _assert_column(self):
        if not self.in_root_array:
            raise JsonRootIsNotArray
        if not self.in_record:
            raise JsonRecordIsNotObject

    def _feed_column(self, value: Optional[CellValue]):
        if self.column is not None:
            self.n_bytes += self.column.feed(self.row, value)
            if self.n_bytes > self.max_bytes:
                raise JsonTooManyBytes
        self.column = None

    def yajl_null(self, _):
        self._assert_column()
        if self.value_stack:
            self.value_stack[-1].append("null")
        else:
            self._feed_column(None)

    def yajl_boolean(self, _, value: int):
        self._assert_column()
        # yajl gives us 0/1. We want true/false.
        # JSON-encode: Workbench does not support boolean
        value_str = "true" if value == 1 else "false"
        if self.value_stack:
            self.value_stack[-1].append(value_str)
        else:
            self._feed_column(value_str)

    def yajl_number(self, _, value_utf8: bytes):
        self._assert_column()
        if self.value_stack:
            self.value_stack[-1].append(_utf8(value_utf8))
        else:
            if b"." in value_utf8:
                value = float(value_utf8)
                if math.isinf(value):
                    raise JsonNumberTooLarge(_utf8(value_utf8))
            else:
                value = int(value_utf8)
                if value.bit_length() > 64:
                    raise JsonNumberTooLarge(_utf8(value_utf8))
            self._feed_column(value)

    def yajl_string(self, _, value_utf8: bytes):
        self._assert_column()
        value = _utf8(value_utf8)
        if self.value_stack:
            self.value_stack[-1].append(json.dumps(value))
        else:
            self._feed_column(value)

    def yajl_start_map(self, _):
        if not self.in_root_array:
            raise JsonRootIsNotArray
        if self.in_record:
            # Begin accumulating JSON-serialized sub-records
            self.value_stack.append([])
        else:
            if self.row >= self.max_rows:
                raise JsonTooManyRows
            self.in_record = True

    def yajl_map_key(self, _, key_utf8: bytes):
        self._assert_column()
        key = _utf8(key_utf8)
        if self.value_stack:
            self.value_stack[-1].append(key)
        else:
            column = self.columns.get(key)
            if not column:
                if len(self.columns) < self.max_cols:
                    column = ColumnBuilder()
                    self.columns[key] = column
                else:
                    self.truncated_columns = True
            self.column = column  # None if we truncated columns

    def yajl_end_map(self, _):
        assert self.in_record
        if self.value_stack:
            # We're serializing a nested value. `self.value_stack` is full of
            # JSON-encoded representations of keys and inner values.
            #
            # Clever hack: zip() the same iter twice for (key, value) pairs
            value_iter = iter(self.value_stack.pop())
            pair_strs = [f"{json.dumps(k)}:{v}" for k, v in zip(value_iter, value_iter)]
            value: str = "{" + ",".join(pair_strs) + "}"
            if self.value_stack:
                # We're deeply nested
                self.value_stack[-1].append(value)
            else:
                # End of an Object cell (which we serialize to JSON)
                self._feed_column(value)
        else:
            # End of a record
            self.column = None
            self.in_record = False
            self.row += 1

    def yajl_start_array(self, _):
        if not self.in_root_array:
            # This is the first token of the whole file
            self.in_root_array = True
            return

        if not self.in_record:
            raise JsonRecordIsNotObject
        assert self.column is not None
        # Begin accumulating JSON-serialized sub-values
        self.value_stack.append([])

    def yajl_end_array(self, _):
        if self.column is None:
            # This is the last token of the whole file
            self.in_root_array = False
            return

        assert self.value_stack
        value = "[" + ",".join(self.value_stack.pop()) + "]"
        if self.value_stack:
            self.value_stack[-1].append(value)
        else:
            # End of an Array cell (which we serialize to JSON)
            self._feed_column(value)


def parse_json_utf8_bytes(bytesio: io.BytesIO) -> ParseJsonResult:
    """
    Parse JSON text into a List of columns.

    * Return error text on invalid JSON ... plus all the data parsed up to the
      error. (Lots of JSON parse errors are "JSON was truncated"; in that case
      we want all the data.)
    * Parse str/int/float as-is; for the rest, concatenate JSON tokens as str.
    * Drop every row starting at MAX_BYTES_PER_TABLE (and warn)
    * Drop every column after MAX_COLUMNS_PER_TABLE (and warn)
    * Drop every row starting at MAX_ROWS_PER_TABLE (and warn)
    """
    content_handler = JsonContentHandler()  # holds our data
    parser = YajlParser(content_handler)
    errors = []
    try:
        parser.parse(bytesio)
    except (JsonRootIsNotArray, JsonRecordIsNotObject):
        errors.append(
            "Workbench cannot import this JSON file. The JSON file "
            "must be an Array of Objects for Workbench to import it."
        )
    except JsonNumberTooLarge as err:
        errors.append(
            f'Stopped parsing JSON because the number "{err.value_str}" '
            "is too large."
        )
    except JsonTooManyRows:
        errors.append("The input had too many rows, so we removed rows.")
    except JsonTooManyBytes:
        errors.append(
            "The input was too large, so we stopped before reading the whole " "file."
        )
    except YajlError as err:
        # e.g., 'lexical error: ...\n    blah\n    ^^here'
        multiline_err = str(err)
        oneline_err = multiline_err.split("\n")[0]
        if (
            content_handler.columns
            and next(iter(content_handler.columns.values())).values
        ):
            errors.append("Stopped parsing after JSON " + oneline_err)
        else:
            errors.append("JSON " + oneline_err)

    if content_handler.truncated_columns:
        errors.append("The input had too many columns, so we removed some.")

    return ParseJsonResult(content_handler.columns, "\n".join(errors))


def _json_columns_to_dataframe_destructive(
    columns: Dict[str, ColumnBuilder]
) -> Tuple[pd.DataFrame, str]:
    """
    Empty a List[ColumnBuilder] to build a pd.DataFrame.

    Why are we destructive (deleting the input list)? Because it saves RAM
    (assuming we don't hold other handles to this list's ColumnBuilders).

    Logic:

    * Column values are assumed to be List[Union[None, str, float, int]]
    * All-NA columns are converted to str
    * All-float/int columns are converted using pd.to_numeric()
    * After that, any mixed-type column is converted to str with a warning
    * Now we only have str; they're converted to category if we expect a
      space savings
    """
    warnings = []
    for name, column in columns.items():
        if not column.value_types:
            series = pd.Series([], dtype=str)
        elif str not in column.value_types:
            series = pd.to_numeric(column.values)
        else:  # it's str
            if len(column.value_types) > 1:
                warnings.append(
                    f'Column "{name}" was mixed-type; we converted it to text.'
                )
                converted = ColumnBuilder()
                for row, value in enumerate(column.values):
                    if value is not None:
                        value = str(value)
                    converted.feed(row, str(value))
                column = converted
            series = pd.Series(column.values, dtype=str)
            if column.should_store_as_categorical:
                series = series.astype("category")
        # overwrite in input dict: that'll save RAM because previous `column`
        # can be garbage-collected
        columns[name] = series
    retval = pd.DataFrame(columns)
    retval.reset_index(drop=True, inplace=True)
    return retval, "\n".join(warnings)


class MimeType(Enum):
    CSV = "text/csv"
    TSV = "text/tab-separated-values"
    TXT = "text/plain"
    JSON = "application/json"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def from_extension(cls, ext: str):
        """
        Find MIME type by extension (e.g., ".txt").

        Raise KeyError if there is none.
        """
        return {
            ".csv": MimeType.CSV,
            ".tsv": MimeType.TSV,
            ".txt": MimeType.TXT,
            ".xls": MimeType.XLS,
            ".xlsx": MimeType.XLSX,
            ".json": MimeType.JSON,
        }[ext]


def _detect_dialect(textio: io.TextIOBase, mime_type: MimeType):
    if mime_type == MimeType.CSV:
        return csv.excel
    elif mime_type == MimeType.TSV:
        return csv.excel_tab
    else:
        sample = textio.read(settings.SEP_DETECT_CHUNK_SIZE)
        textio.seek(0)
        return csv.Sniffer().sniff(sample, ",;\t")


@contextmanager
def open_path_with_autodetected_charset(path: pathlib.Path):
    with path.open("rb") as bytesio:
        # TODO handle encoding error
        encoding = detect_encoding(bytesio)
        bytesio.seek(0)
        with wrap_text(bytesio, encoding) as textio:
            yield textio


def parse_text(textio, ext, has_header):
    dialect = _detect_dialect(textio, ext)
    parse_table_result = parse_table(textio, dialect)

    if not len(parse_table_result.columns):
        return "This file is empty"  # error: this is never the user's intent
    dataframe = _csv_columns_to_dataframe_destructive(
        parse_table_result.columns, has_header
    )
    error = parse_table_result.error
    if error:
        return {"dataframe": dataframe, "error": error}
    else:
        return dataframe


def parse_text_bytesio(
    bytesio, encoding: Optional[str], mime_type: MimeType, has_header: bool
):
    if encoding is None:
        encoding = detect_encoding(bytesio)
    with wrap_text(bytesio, encoding) as textio:
        return parse_text(textio, mime_type, has_header)


class EncodedTextReader(io.RawIOBase):
    def __init__(
        self, textio, encoding, buffer_size=io.DEFAULT_BUFFER_SIZE, errors="strict"
    ):
        self.textio = textio
        self.buffer_size = io.DEFAULT_BUFFER_SIZE  # characters
        self.encoder = codecs.lookup(encoding).incrementalencoder(errors=errors)
        self.block: bytes = b""
        self.block_pos: int = 0  # how much of `block` we've already read

    # override io.IOBase
    def close(self):
        self.textio.close()
        super().close()

    # override io.IOBase
    def readable(self):
        return True

    # override io.IOBase
    def writable(self):
        return False

    # override io.RawIOBase
    def readinto(self, b: bytes) -> int:
        if self.block_pos == len(self.block):
            # Read another block
            self.block = self.encoder.encode(self.textio.read(self.buffer_size))
            self.block_pos = 0
            if not self.block:
                return 0  # end of file
        pos = self.block_pos
        nread = min(len(b), len(self.block) - pos)
        b[:nread] = self.block[pos : pos + nread]
        self.block_pos = pos + nread
        return nread


@contextmanager
def bytes_transcoded_to_utf8(bytesio, encoding: Optional[str]):
    """
    Opens `path`, yielding a utf-8-encoded BytesIO.
    """
    # TODO handle encoding error
    if encoding is None:
        encoding = detect_encoding(bytesio)
    bytesio.seek(0)
    if encoding == "utf-8":
        yield bytesio
    else:
        with wrap_text(bytesio, encoding) as textio:
            with EncodedTextReader(textio, "utf-8", errors="replace") as encodedio:
                yield encodedio


def parse_utf8_json(bytesio):
    parse_json_result = parse_json_utf8_bytes(bytesio)
    errors = []
    if parse_json_result.error:
        errors.append(parse_json_result.error)
    dataframe, warnings = _json_columns_to_dataframe_destructive(
        parse_json_result.columns
    )
    if warnings:
        errors.append(warnings)
    error = "\n".join(errors)
    if error:
        return {"dataframe": dataframe, "error": error}
    else:
        return dataframe


def parse_json_bytesio(bytesio, encoding: Optional[str]):
    with bytes_transcoded_to_utf8(bytesio, encoding) as utf8_bytesio:
        return parse_utf8_json(utf8_bytesio)


def parse_wrongly(bytesio, encoding: Optional[str], mime_type: str, has_header: bool):
    """
    Delegate to modules.utils.parse_bytesio(), which is wrong.

    It's wrong because we parse as though `has_header` is True and then we
    break everything by calling turn_header_into_first_row() if `has_header`
    is False.
    """
    result = bad_parse_bytesio(bytesio, mime_type, encoding)
    result.truncate_in_place_if_too_big()
    dataframe = result.dataframe
    error = result.error
    if not has_header:
        dataframe = turn_header_into_first_row(dataframe)
    if error:
        if dataframe.empty:
            return error
        else:
            return {"dataframe": dataframe, "error": error}
    else:
        return dataframe


def parse_file(path: pathlib.Path, has_header: bool):
    ext = "".join(path.suffixes).lower()
    try:
        mime_type = MimeType.from_extension(ext)
    except KeyError:
        return "Unknown file extension %r. Please upload a different file." % ext
    with path.open("rb") as bytesio:
        return _do_parse_bytesio(bytesio, None, mime_type, has_header)


def parse_bytesio(
    bytesio: io.BytesIO, encoding: Optional[str], content_type: str, has_header: bool
):
    """
    Parse bytes, given a content_type and encoding (e.g., from HTTP headers).

    `bytesio` must be seekable. `encoding` is optional.
    """
    try:
        mime_type = MimeType(content_type)
    except ValueError:
        return "Unknown MIME type %r. Please choose a different file." % content_type
    return _do_parse_bytesio(bytesio, encoding, mime_type, has_header)


def _do_parse_bytesio(
    bytesio: io.BytesIO, encoding: Optional[str], mime_type: MimeType, has_header: bool
):
    if mime_type in {MimeType.CSV, MimeType.TSV, MimeType.TXT}:
        return parse_text_bytesio(bytesio, encoding, mime_type, has_header)
    elif mime_type == MimeType.JSON:
        return parse_json_bytesio(bytesio, encoding)
    else:
        return parse_wrongly(bytesio, encoding, mime_type.value, has_header)
