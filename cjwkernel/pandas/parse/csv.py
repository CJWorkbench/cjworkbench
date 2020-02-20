import array
import contextlib
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from typing import List, Optional, Tuple
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context
from cjwmodule.util.colnames import gen_unique_clean_colnames
from .postprocess import dictionary_encode_columns, infer_table_metadata
from .text import transcode_to_utf8_and_warn


class ParseCsvWarning:
    pass


@dataclass(frozen=True)
class ParseCsvWarningSkippedRows(ParseCsvWarning):
    n_rows_skipped: int
    max_n_rows: int

    def __str__(self):  # TODO nix when we support i18n
        return "Skipped %d rows (after limit of %d)" % (
            self.n_rows_skipped,
            self.max_n_rows,
        )


@dataclass(frozen=True)
class ParseCsvWarningSkippedColumns(ParseCsvWarning):
    n_columns_skipped: int
    max_n_columns: int

    def __str__(self):  # TODO nix when we support i18n
        return "Skipped %d columns (after limit of %d)" % (
            self.n_columns_skipped,
            self.max_n_columns,
        )


@dataclass(frozen=True)
class ParseCsvWarningTruncatedValues(ParseCsvWarning):
    n_values_truncated: int
    max_bytes_per_value: int
    first_value_row: int
    first_value_column: int

    def __str__(self):  # TODO nix when we support i18n
        return "Truncated %d values (to %d bytes each; see row %d column %d)" % (
            self.n_values_truncated,
            self.max_bytes_per_value,
            self.first_value_row,
            self.first_value_column,
        )


@dataclass(frozen=True)
class ParseCsvWarningCleanedAsciiColumnNames(ParseCsvWarning):
    n_names: int
    first_name: str

    def __str__(self):  # TODO nix when we support i18n
        return ("Removed special characters from %d column names (see “%s”)") % (
            self.n_names,
            self.first_name,
        )


@dataclass(frozen=True)
class ParseCsvWarningNumberedColumnNames(ParseCsvWarning):
    n_names: int
    first_name: str

    def __str__(self):  # TODO nix when we support i18n
        return "Renamed %d duplicate column names (see “%s”)" % (
            self.n_names,
            self.first_name,
        )


@dataclass(frozen=True)
class ParseCsvWarningTruncatedColumnNames(ParseCsvWarning):
    n_names: int
    first_name: str

    def __str__(self):  # TODO nix when we support i18n
        return "Truncated %d column names (to %d bytes each; see “%s”)" % (
            self.n_names,
            settings.MAX_BYTES_PER_COLUMN_NAME,
            self.first_name,
        )


@dataclass(frozen=True)
class ParseCsvWarningRepairedValues(ParseCsvWarning):
    n_values_repaired: int
    first_value_row: int
    first_value_column: int

    def __str__(self):  # TODO nix when we support i18n
        return (
            "Repaired %d values which misused quotation marks (see row %d column %d)"
            % (self.n_values_repaired, self.first_value_row, self.first_value_column)
        )


@dataclass(frozen=True)
class ParseCsvWarningRepairedEndOfFile(ParseCsvWarning):
    def __str__(self):  # TODO nix when we support i18n
        return "Inserted missing quotation mark at end of file"


@dataclass(frozen=True)
class ParseCsvWarningTruncatedFile(ParseCsvWarning):
    original_n_bytes: int
    max_n_bytes: int

    def __str__(self):  # TODO nix when we support i18n
        return "Truncated %d bytes from file (maximum is %d bytes)" % (
            self.original_n_bytes - self.max_n_bytes,
            self.max_n_bytes,
        )


@dataclass(frozen=True)
class ParseCsvWarningRepairedEncoding(ParseCsvWarning):
    encoding: str
    first_invalid_byte: int
    first_invalid_byte_position: int

    def __str__(self):  # TODO nix when we support i18n
        return (
            "Encoding error: byte 0x%02X is invalid %s at byte %d. "
            "We replaced invalid bytes with “�”."
        ) % (self.first_invalid_byte, self.encoding, self.first_invalid_byte_position)


ParseCsvWarning.RepairedEndOfFile = ParseCsvWarningRepairedEndOfFile
ParseCsvWarning.RepairedEncoding = ParseCsvWarningRepairedEncoding
ParseCsvWarning.RepairedValues = ParseCsvWarningRepairedValues
ParseCsvWarning.SkippedColumns = ParseCsvWarningSkippedColumns
ParseCsvWarning.SkippedRows = ParseCsvWarningSkippedRows
ParseCsvWarning.TruncatedFile = ParseCsvWarningTruncatedFile
ParseCsvWarning.TruncatedValues = ParseCsvWarningTruncatedValues
ParseCsvWarning.CleanedAsciiColumnNames = ParseCsvWarningCleanedAsciiColumnNames
ParseCsvWarning.NumberedColumnNames = ParseCsvWarningNumberedColumnNames
ParseCsvWarning.TruncatedColumnNames = ParseCsvWarningTruncatedColumnNames


_PATTERN_SKIPPED_ROWS = re.compile(r"^skipped (\d+) rows \(after row limit of (\d+)\)$")
_PATTERN_SKIPPED_COLUMNS = re.compile(
    r"^skipped (\d+) columns \(after column limit of (\d+)\)$"
)
_PATTERN_TRUNCATED_VALUES = re.compile(
    r"^truncated (\d+) values \(value byte limit is (\d+); see row (\d+) column (\d+)\)$"
)
_PATTERN_REPAIRED_VALUES = re.compile(
    r"^repaired (\d+) values \(misplaced quotation marks; see row (\d+) column (\d+)\)$"
)
_PATTERN_REPAIRED_END_OF_FILE = re.compile(
    r"^repaired last value \(missing quotation mark\)$"
)


def _parse_csv_to_arrow_warning(line: str) -> ParseCsvWarning:
    """
    Parse a single line of csv-to-arrow output.

    Raise RuntimeError if a line cannot be parsed. (We can't recover from that
    because we don't know what's happening.)
    """
    m = _PATTERN_SKIPPED_ROWS.match(line)
    if m is not None:
        return ParseCsvWarning.SkippedRows(
            n_rows_skipped=int(m.group(1)), max_n_rows=int(m.group(2))
        )
    m = _PATTERN_SKIPPED_COLUMNS.match(line)
    if m is not None:
        return ParseCsvWarning.SkippedColumns(
            n_columns_skipped=int(m.group(1)), max_n_columns=int(m.group(2))
        )
    m = _PATTERN_TRUNCATED_VALUES.match(line)
    if m is not None:
        return ParseCsvWarning.TruncatedValues(
            n_values_truncated=int(m.group(1)),
            max_bytes_per_value=int(m.group(2)),
            first_value_row=int(m.group(3)),
            first_value_column=int(m.group(4)),
        )
    m = _PATTERN_REPAIRED_VALUES.match(line)
    if m is not None:
        return ParseCsvWarning.RepairedValues(
            n_values_repaired=int(m.group(1)),
            first_value_row=int(m.group(2)),
            first_value_column=int(m.group(3)),
        )
    m = _PATTERN_REPAIRED_END_OF_FILE.match(line)
    if m is not None:
        return ParseCsvWarning.RepairedEndOfFile()
    raise RuntimeError("Could not parse csv-to-arrow output line: %r" % line)


def _parse_csv_to_arrow_warnings(text: str) -> List[ParseCsvWarning]:
    return [_parse_csv_to_arrow_warning(line) for line in text.split("\n") if line]


def _postprocess_name_columns(
    table: pyarrow.Table, has_header: bool
) -> Tuple[pyarrow.Table, List[ParseCsvWarning]]:
    """
    Return `table`, with final column names but still String values.
    """
    warnings = []
    if has_header and table.num_rows > 0:
        n_ascii_cleaned = 0
        first_ascii_cleaned = None
        n_truncated = 0
        first_truncated = None
        n_numbered = 0
        first_numbered = None

        names = []
        for colname in gen_unique_clean_colnames(
            list(("" if c[0] is pyarrow.NULL else c[0].as_py()) for c in table.columns),
            settings=settings,
        ):
            names.append(colname.name)
            if colname.is_ascii_cleaned:
                if n_ascii_cleaned == 0:
                    first_ascii_cleaned = colname.name
                n_ascii_cleaned += 1
            if colname.is_truncated:
                if n_truncated == 0:
                    first_truncated = colname.name
                n_truncated += 1
            if colname.is_numbered:
                if n_numbered == 0:
                    first_numbered = colname.name
                n_numbered += 1
            # Unicode can't be fixed, because we assume valid UTF-8 input
            assert not colname.is_unicode_fixed
            # Stay silent if colname.is_default. Users expect us to
            # auto-generate default column names.

        if n_ascii_cleaned:
            warnings.append(
                ParseCsvWarning.CleanedAsciiColumnNames(
                    n_ascii_cleaned, first_ascii_cleaned
                )
            )
        if n_truncated:
            warnings.append(
                ParseCsvWarning.TruncatedColumnNames(n_truncated, first_truncated)
            )
        if n_numbered:
            warnings.append(
                ParseCsvWarning.NumberedColumnNames(n_numbered, first_numbered)
            )

        # Remove header (zero-copy: builds new pa.Table with same backing data)
        table = table.slice(1)
    else:
        names = [f"Column {i + 1}" for i in range(len(table.columns))]

    return (
        pyarrow.table({name: table.column(i) for i, name in enumerate(names)}),
        warnings,
    )


def _nix_utf8_chunk_empty_strings(chunk: pyarrow.Array) -> pyarrow.Array:
    """
    Return a pa.Array that replaces "" with null.

    Assume `arr` is of type `utf8` or a dictionary of `utf8`.
    """
    # pyarrow's cast() can't handle empty string. Create a new Array with
    # "" changed to null.
    _, offsets_buf, data_buf = chunk.buffers()

    # Build a new validity buffer, based on offsets. Empty string = null.
    # Assume `data` has no padding bytes in the already-null values. That way
    # we can ignore the _original_ validity buffer and assume all original
    # values are not-null. (Null values are stored as "" plus "invalid".)
    #
    # Validity-bitmap spec:
    # https://arrow.apache.org/docs/format/Columnar.html#validity-bitmaps

    # first offset must be 0. Next offsets are used to calculate lengths
    offsets = array.array("i")
    assert offsets.itemsize == 4
    offsets.frombytes(offsets_buf)
    if sys.byteorder != "little":
        offsets.byteswap()  # pyarrow is little-endian

    validity = bytearray()
    null_count = 0
    last_offset = offsets[0]
    assert last_offset == 0
    pos = 1
    while True:
        # Travel offsets in strides of 8: one per char in the validity bitmap.
        # Pad with an extra 1 bit -- [2020-02-20, adamhooper] I think I read
        # this is needed somewhere.
        valid_byte = 0x00
        block = offsets[pos : pos + 8]
        try:
            if block[0] > last_offset:
                valid_byte |= 0x1
            else:
                null_count += 1
            if block[1] > block[0]:
                valid_byte |= 0x2
            else:
                null_count += 1
            if block[2] > block[1]:
                valid_byte |= 0x4
            else:
                null_count += 1
            if block[3] > block[2]:
                valid_byte |= 0x8
            else:
                null_count += 1
            if block[4] > block[3]:
                valid_byte |= 0x10
            else:
                null_count += 1
            if block[5] > block[4]:
                valid_byte |= 0x20
            else:
                null_count += 1
            if block[6] > block[5]:
                valid_byte |= 0x40
            else:
                null_count += 1
            if block[7] > block[6]:
                valid_byte |= 0x80
            else:
                null_count += 1
            validity.append(valid_byte)
            last_offset = block[7]
            pos += 8
        except IndexError:
            validity.append(valid_byte)
            break  # end of offsets

    validity_buf = pyarrow.py_buffer(validity)

    # We may have over-counted in null_count: anything before `chunk.offset`
    # should not count.
    #
    # It's less work to "undo" the counting we did before -- otherwise we'd
    # riddle the above loop with if-statements.
    for i in range(chunk.offset):
        if offsets[i + 1] == offsets[i]:
            null_count -= 1

    return pyarrow.StringArray.from_buffers(
        length=len(chunk),
        value_offsets=offsets_buf,
        data=data_buf,
        null_bitmap=validity_buf,
        null_count=null_count,
        offset=chunk.offset,
    )


def _autocast_column(data: pyarrow.ChunkedArray) -> pyarrow.ChunkedArray:
    """
    Convert `data` to float64 or int(64|32|16|8); as fallback, return `data`.

    Assume `data` is of type `utf8` or a dictionary of utf8.

    *Implementation wart*: this may choose float64 when integers would seem a
    better choice, because we use Pandas and Pandas does not support nulls
    in integer columns.
    """
    # All-empty (and all-null) columns stay text
    for chunk in data.chunks:
        # https://arrow.apache.org/docs/format/Columnar.html#variable-size-binary-layout
        _, offsets_buf, _ = chunk.buffers()
        # If data has an offset, ignore what comes before
        #
        # We don't need to grab the _int_ offset: we can just look at the
        # byte-representation of it.
        offset_0_buf = offsets_buf[chunk.offset * 4 : (chunk.offset + 1) * 4]
        # last offset isn't always the last 4 bytes: there can be padding
        offset_n_buf = offsets_buf[
            (chunk.offset + len(chunk)) * 4 : (chunk.offset + len(chunk) + 1) * 4
        ]
        if offset_0_buf.to_pybytes() != offset_n_buf.to_pybytes():
            # there's at least 1 byte of text. (Assumes the CSV reader doesn't
            # pad the buffer with gibberish.)
            break
    else:
        # there are 0 bytes of text
        return data

    # Convert "" => null, so pyarrow cast() won't balk at it.
    sane = pyarrow.chunked_array(
        [_nix_utf8_chunk_empty_strings(chunk) for chunk in data.chunks]
    )

    try:
        numbers = sane.cast(pyarrow.float64())
    except pyarrow.ArrowInvalid:
        # Some string somewhere wasn't a number
        return data

    # Downcast integers, when possible.
    #
    # We even downcast float to int. Workbench semantics say a Number is a
    # Number; so we might as well store it efficiently.
    try:
        # Shrink as far as we can, until pyarrow complains.
        #
        # pyarrow will error "Floating point value truncated" if a conversion
        # from float to int would be lossy.
        #
        # We'll return the last _successful_ `numbers` result.
        numbers = numbers.cast(pyarrow.int32())
        numbers = numbers.cast(pyarrow.int16())
        numbers = numbers.cast(pyarrow.int8())
    except pyarrow.ArrowInvalid:
        pass

    return numbers


def _postprocess_autocast_columns(table: pyarrow.Table) -> pyarrow.Table:
    return pyarrow.table(
        {
            name: _autocast_column(column)
            for name, column in zip(table.column_names, table.columns)
        }
    )


def _postprocess_table(
    table: pyarrow.Table, has_header: bool, autoconvert_text_to_numbers: bool
) -> Tuple[pyarrow.Table, List[ParseCsvWarning]]:
    """
    Transform `raw_table` to meet our standards:

    * If `has_headers` is True, remove the first row (zero-copy) and use it to
      build column names -- which we guarantee are unique. Otherwise, generate
      unique column names.
    * Auto-convert each column to numeric if every value is represented
      correctly. (`""` becomes `null`. This conversion is lossy for the myriad
      numbers CSV can represent accurately that int/double cannot.
      TODO auto-conversion optional.)
    * Convert each utf8 column to dictionary if it agrees with
      `settings.MAX_DICTIONARY_PYLIST_N_BYTES` and
      `settings.MIN_DICTIONARY_COMPRESSION_RATIO`.
    """
    table, warnings = _postprocess_name_columns(table, has_header)
    if autoconvert_text_to_numbers:
        table = _postprocess_autocast_columns(table)
    table = dictionary_encode_columns(table)
    return table, warnings


def detect_delimiter(path: Path):
    with path.open("r", encoding="utf-8") as textio:
        sample = textio.read(settings.SEP_DETECT_CHUNK_SIZE)

    try:
        dialect = csv.Sniffer().sniff(sample, ",;\t")
    except csv.Error:
        # When in doubt, CSV. (We have no logic to handle an exception.)
        dialect = csv.excel

    return dialect.delimiter


@dataclass(frozen=True)
class ParseCsvResult:
    """TODO when we support multiple RenderErrors, nix this and use RenderError."""

    table: pyarrow.Table
    warnings: List[ParseCsvWarning]


def _parse_csv(
    path: Path,
    *,
    encoding: Optional[str],
    delimiter: Optional[str],
    has_header: bool,
    autoconvert_text_to_numbers: bool,
) -> ParseCsvResult:
    """
    Parse CSV, TSV or other delimiter-separated text file.

    Raise LookupError for an `encoding` Python cannot handle.

    Raise UnicodeError when the file simply cannot be read as text. (e.g., a
    UTF-16 file that does not start with a byte-order marker.)

    The process:

    1. Truncate the file to our maximum size. (WARNING This is destructive!)
       (TODO if any caller minds the truncation, fix this logic.)
    2. Convert the file to UTF-8.
    3. Sniff delimiter, if the passed argument is `None`.
    4. Run `csv-to-arrow` to parse the CSV into unnamed columns.
    5. Postprocess each column: remove its header if needed and
       dictionary-encode if it's helpful. (This doesn't cost much RAM per
       column: either dictionary encoding makes it small, or it's a zero-copy
       slice of the csv-to-arrow output file.)
    6. Write the final Arrow file.
    """
    warnings = []

    with contextlib.ExitStack() as ctx:
        n_bytes = path.stat().st_size
        if n_bytes > settings.MAX_CSV_BYTES:
            # We can't simply os.truncate() the input file, because sandboxed code
            # can't modify input files.
            truncated_path = ctx.enter_context(tempfile_context(prefix="truncated-"))
            with path.open("rb") as src, truncated_path.open("wb") as dest:
                os.sendfile(dest.fileno(), src.fileno(), 0, settings.MAX_CSV_BYTES)
            path = truncated_path
            warnings.append(
                ParseCsvWarning.TruncatedFile(
                    original_n_bytes=n_bytes, max_n_bytes=settings.MAX_CSV_BYTES
                )
            )

        utf8_path = ctx.enter_context(tempfile_context(prefix="utf8-", suffix=".txt"))
        # raises LookupError, UnicodeError
        transcode_warning = transcode_to_utf8_and_warn(path, utf8_path, encoding)
        if transcode_warning is not None:
            warnings.append(
                ParseCsvWarning.RepairedEncoding(
                    encoding=transcode_warning.encoding,
                    first_invalid_byte=transcode_warning.first_invalid_byte,
                    first_invalid_byte_position=transcode_warning.first_invalid_byte_position,
                )
            )

        # Sniff delimiter
        if not delimiter:
            delimiter = detect_delimiter(utf8_path)

        with tempfile_context(suffix=".arrow") as arrow_path:
            # raise subprocess.CalledProcessError on error ... but there is no
            # error csv-to-arrow will throw that we can recover from.
            child = subprocess.run(
                [
                    "/usr/bin/csv-to-arrow",
                    "--delimiter",
                    delimiter,
                    "--max-rows",
                    str(settings.MAX_ROWS_PER_TABLE),
                    "--max-columns",
                    str(settings.MAX_COLUMNS_PER_TABLE),
                    "--max-bytes-per-value",
                    str(settings.MAX_BYTES_PER_VALUE),
                    utf8_path.as_posix(),
                    arrow_path.as_posix(),
                ],
                capture_output=True,
                check=True,
            )
            if child.stdout:
                warnings.extend(
                    _parse_csv_to_arrow_warnings(child.stdout.decode("utf-8"))
                )

            reader = pyarrow.ipc.open_file(arrow_path.as_posix())
            raw_table = reader.read_all()  # efficient -- RAM is mmapped

    table, more_warnings = _postprocess_table(
        raw_table, has_header, autoconvert_text_to_numbers
    )
    return ParseCsvResult(table, warnings + more_warnings)


def parse_csv(
    path: Path,
    *,
    output_path: Path,
    encoding: Optional[str],
    delimiter: Optional[str],
    has_header: bool,
    autoconvert_text_to_numbers: bool,
) -> RenderResult:
    result = _parse_csv(
        path,
        encoding=encoding,
        delimiter=delimiter,
        has_header=has_header,
        autoconvert_text_to_numbers=autoconvert_text_to_numbers,
    )
    with pyarrow.ipc.RecordBatchFileWriter(
        output_path.as_posix(), schema=result.table.schema
    ) as writer:
        writer.write_table(result.table)

    metadata = infer_table_metadata(result.table)

    if len(metadata.columns) == 0:
        arrow_table = ArrowTable()
    else:
        arrow_table = ArrowTable(output_path, result.table, metadata)
    if result.warnings:
        # TODO when we support i18n, this will be even simpler....
        en_message = "\n".join([str(warning) for warning in result.warnings])
        errors = [RenderError(I18nMessage.TODO_i18n(en_message))]
    else:
        errors = []

    return RenderResult(arrow_table, errors)
