import contextlib
import csv
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import List, Optional
import pandas as pd
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context
from cjwkernel.pandas.moduleutils import uniquize_colnames
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


def _postprocess_name_columns(table: pyarrow.Table, has_header: bool) -> pyarrow.Table:
    """
    Return `table`, with final column names but still String values.
    """
    if has_header and table.num_rows > 0:
        column_names = list(
            uniquize_colnames(
                (c[0].as_py() or f"Column {i + 1}") for i, c in enumerate(table.columns)
            )
        )
        # Remove header (zero-copy: builds new pa.Table with same backing data)
        table = table.slice(1)
    else:
        column_names = [f"Column {i + 1}" for i in range(len(table.columns))]

    return pyarrow.table(
        {column_names[i]: table.columns[i] for i in range(len(table.columns))}
    )


def _autocast_column(data: pyarrow.ChunkedArray) -> pyarrow.ChunkedArray:
    """
    Convert `data` to float64 or int(64|32|16|8); as fallback, return `data`.

    Assume `data` is of type `utf8` or a dictionary of utf8.

    *Implementation wart*: this may choose float64 when integers would seem a
    better choice, because we use Pandas and Pandas does not support nulls
    in integer columns.
    """
    series: pd.Series = data.to_pandas()
    null = series.isnull()
    empty = series == ""
    if empty.any() and (null | empty).all():
        # All-empty (and all-null) columns stay text
        return data
    try:
        # Try to cast to numbers
        numbers = pyarrow.chunked_array([pd.to_numeric(series).values])
    except (ValueError, TypeError):
        return data

    # Downcast integers, when possible.
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
) -> pyarrow.Table:
    """
    Transform `raw_table` to meet our standards:

    * If `has_headers` is True, remove the first row (zero-copy) and use it to
      build column names -- which we guarantee are unique. Otherwise, generate
      unique column names.
    * Convert each column dictionary if it agrees with
      `settings.MAX_DICTIONARY_PYLIST_N_BYTES` and
      `settings.MIN_DICTIONARY_COMPRESSION_RATIO`.
    * Auto-convert each column to numeric if every value is represented
      correctly. (`""` becomes `null`. This conversion is lossy for the myriad
      numbers CSV can represent accurately that int/double cannot.
      TODO auto-conversion optional.)
    """
    table = _postprocess_name_columns(table, has_header)
    table = dictionary_encode_columns(table)
    if autoconvert_text_to_numbers:
        table = _postprocess_autocast_columns(table)
    return table


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

    table = _postprocess_table(raw_table, has_header, autoconvert_text_to_numbers)
    return ParseCsvResult(table, warnings)


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
        arrow_table = ArrowTable(output_path, metadata)
    if result.warnings:
        # TODO when we support i18n, this will be even simpler....
        en_message = "\n".join([str(warning) for warning in result.warnings])
        errors = [RenderError(I18nMessage.TODO_i18n(en_message))]
    else:
        errors = []

    return RenderResult(arrow_table, errors)
