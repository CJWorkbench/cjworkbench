import csv
from dataclasses import dataclass
import io
import pathlib
import sys
from typing import List
from django.conf import settings
import pandas as pd
from .utils import detect_encoding, wrap_text, uniquize_colnames, \
        autocast_series_dtype, turn_header_into_first_row, parse_bytesio



class ColumnBuilder:
    """
    Compact accumulator of CSV Strings for a column.

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
    * We only support str. (Casting comes after parsing.)
    * We aren't like the Pandas C engine: we parse text, not bytes. (Pandas
      C engine re-encodes the entire file to UTF-8 before parsing.)
    * We aren't C-optimized (yet).
    """
    def __init__(self):
        self._intern = {}  # hash of str to itself
        self.n_bytes = 0
        self.n_values = 0  # number of non-NA values
        self.values = []  # list of (interned) str or None (None means NA)

    def feed(self, row: int, value: str):
        """
        Feed a new value.

        If `row` is greater than `len(self.values)`, fill in `None` 

        Return number of bytes we're costing.
        """
        interned_value = self._intern.setdefault(value, value)
        n_na_to_prepend = row - len(self.values)

        for _ in range(n_na_to_prepend):
            self.values.append(None)
        self.values.append(interned_value)
        self.n_values += 1

        return (
            n_na_to_prepend * 8  # newly-added NA values
            + 8                  # pointer in self.values
            + 8                  # hash-table entry
            + (sys.getsizeof(value) if value is interned_value else 0)
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
        n_unique = len(self._intern)

        # for now, magic number: "categorical is <80% the size of list"
        return n_unique / self.n_values < 0.8


@dataclass
class ParseTableResult:
    columns: List[ColumnBuilder]
    error: str


def parse_table(textio: io.TextIOBase,
                dialect: csv.Dialect) -> ParseTableResult:
    """
    Convert CSV to DataFrame.

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
            'The input was too large, so we removed %d rows'
            % (n_input_rows - len(columns[0].values))
        )
    if n_input_columns is not None:
        warnings.append(
            'The input had too many columns, so we removed %d columns'
            % (n_input_columns - MAX_COLUMNS)
        )

    return ParseTableResult(columns, '\n'.join(warnings))


def _columns_to_dataframe_destructive(columns: List[ColumnBuilder],
                                      has_header: bool) -> pd.DataFrame:
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
    colnames = list(uniquize_colnames(
        c.values[0] if has_header and c.values[0] else f'Column {i + 1}'
        for i, c in enumerate(columns)
    ))

    for i, colname in enumerate(colnames):
        column = columns[i]
        values = column.values
        if has_header:
            values = values[1:]
        series = autocast_series_dtype(pd.Series(values, name=colname))
        if series.dtype == object and column.should_store_as_categorical:
            series = series.astype('category')
        # modify `columns` in-place: frees RAM `columns[i]` RAM
        columns[i] = series

    return pd.DataFrame({s.name: s for s in columns})


_ExtensionMimeTypes = {
    '.xls': 'application/vnd.ms-excel',
    '.xlsx':
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.json': 'application/json',
}


def _detect_dialect(textio: io.TextIOBase, ext: str):
    if ext == '.csv':
        return csv.excel
    elif ext == '.tsv':
        return csv.excel_tab
    else:
        sample = textio.read(settings.SEP_DETECT_CHUNK_SIZE)
        textio.seek(0)
        return csv.Sniffer().sniff(sample, ',;\t')


def parse_text(path, ext, has_header):
    with path.open('rb') as bytesio:
        # TODO handle encoding error
        encoding = detect_encoding(bytesio)
        bytesio.seek(0)
        with wrap_text(bytesio, encoding) as textio:
            dialect = _detect_dialect(textio, ext)
            parse_table_result = parse_table(textio, dialect)

    if not len(parse_table_result.columns):
        return 'This file is empty'  # error: this is never the user's intent
    dataframe = _columns_to_dataframe_destructive(parse_table_result.columns,
                                                  has_header)
    error = parse_table_result.error
    if error:
        return {'dataframe': dataframe, 'error': error}
    else:
        return dataframe


def parse_wrongly(path: pathlib.Path, mime_type: str, has_header: bool):
    """
    Delegate to modules.utils.parse_bytesio(), which is wrong.

    It's wrong because we parse as though `has_header` is True and then we
    break everything by calling turn_header_into_first_row() if `has_header`
    is False.
    """
    with path.open('rb') as f:
        result = parse_bytesio(f, mime_type)
    result.truncate_in_place_if_too_big()
    dataframe = result.dataframe
    error = result.error
    if not has_header:
        dataframe = turn_header_into_first_row(dataframe)
    if error:
        if dataframe.empty:
            return error
        else:
            return {'dataframe': dataframe, 'error': error}
    else:
        return dataframe


def parse_file(path: pathlib.Path, has_header: bool):
    ext = ''.join(path.suffixes)
    if ext in ['.csv', '.tsv', '.txt']:
        return parse_text(path, ext, has_header)
    mime_type = _ExtensionMimeTypes.get(ext, None)
    if mime_type:
        return parse_wrongly(path, mime_type, has_header)
    else:
        return (
            'Unknown file extension %r. Please upload a different file.' % ext
        )
