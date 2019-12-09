import contextlib
import io
import logging
from pathlib import Path
import subprocess
from typing import Any, ContextManager, Dict, List
import pyarrow
import pyarrow.parquet
from cjwkernel.util import tempfile_context


logger = logging.getLogger(__name__)


def file_has_parquet_magic_number(path: Path) -> bool:
    """
    Detect Parquet.

    A Parquet file starts and ends with "PAR1" (ASCII-encoded).
    """
    with path.open("rb", buffering=0) as f:
        if f.read(4) != b"PAR1":
            return False

        # fseek(-4, SEEK_END) shouldn't error EINVAL: we know the file is >=4
        # bytes long because we'd have returned above if it were shorter.
        if f.seek(-4, io.SEEK_END) < 16:
            # The file may start and end with "PAR1" (or it may _be_ "PAR1" on
            # its own, if f.seek() returns 0); but it's too small to be a
            # Parquet file.
            #
            # Parquet file has a certain amount of Thrift; let's ignore Thrift
            # overhead and picture the minimum file:
            #
            #     "PAR1" magic number (4)
            #     File metadata:
            #         i32 version (4)
            #         i64 number of rows (8)
            #     i32 length of file metadata (4)
            #     "PAR1" magic number (4)
            #
            # An inane empty Parquet file -- impossible because Thrift adds
            # overhead -- would be 20 bytes long.
            #
            # So if we seeked to 4 bytes from the end and we aren't at _least_
            # 16 bytes in, we know for sure the file isn't Parquet.
            return False
        if f.read(4) != b"PAR1":
            return False

    return True


def convert_parquet_file_to_arrow_file(parquet_path: Path, arrow_path: Path) -> None:
    result = subprocess.run(
        ["/usr/bin/parquet-to-arrow", str(parquet_path), str(arrow_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        # We don't handle TimeoutException at all: conversion should always be
        # quick. If it takes longer than 60s that's certainly a bug in
        # parquet-to-arrow; crash and email us so we can fix it ASAP.
        timeout=60,  # should never time out
    )
    if result.stdout:
        logger.error(
            "parquet-to-arrow wrote to stdout! That's a bug. It wrote: %s",
            result.stdout,
        )
    if result.returncode != 0:
        raise pyarrow.ArrowIOError(result.stderr)


def are_files_equal(path1: Path, path2: Path) -> bool:
    result = subprocess.run(
        ["/usr/bin/parquet-diff", str(path1), str(path2)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        # We don't handle TimeoutException at all: conversion should always be
        # quick. If it takes longer than 60s that's certainly a bug in
        # parquet-to-arrow; crash and email us so we can fix it ASAP.
        timeout=60,  # should never time out
    )
    if result.returncode == 0:
        return True  # files are same
    elif result.returncode == 1:
        return False  # and ignore message -- it's a debug message
    else:
        raise pyarrow.ArrowIOError(result.stdout)


def write(parquet_path: Path, table: pyarrow.Table) -> None:
    """
    Write an Arrow table to a Parquet file, overwriting if needed.

    We aim to keep the file format "stable": all future versions of
    parquet.read() should support all files written by today's version of this
    function.

    Dictionary-encoded columns will stay dictionary-encoded. Practically,
    `parquet.write(path, table); table = parquet.read(path)` does not change
    `table`.
    """
    if table.num_rows == 0:
        # Workaround for https://issues.apache.org/jira/browse/ARROW-6568
        # If table is zero-length, guarantee it has a RecordBatch so Arrow
        # won't crash when writing a DictionaryArray.

        def empty_array_for_field(field):
            if pyarrow.types.is_dictionary(field.type):
                return pyarrow.DictionaryArray.from_arrays(
                    pyarrow.array([], type=field.type.index_type),
                    pyarrow.array([], type=field.type.value_type),
                )
            else:
                return pyarrow.array([], type=field.type)

        table = pyarrow.table(
            {field.name: empty_array_for_field(field) for field in table.schema}
        )

    pyarrow.parquet.write_table(
        table,
        str(parquet_path),
        version="2.0",
        compression="SNAPPY",
        # Preserve whatever dictionaries we have in Pandas. Write+read
        # should return an exact copy.
        use_dictionary=[
            name.encode("utf-8")
            for name, column in zip(table.column_names, table.columns)
            if pyarrow.types.is_dictionary(column.type)
        ],
    )


@contextlib.contextmanager
def open_as_mmapped_arrow(parquet_path: Path) -> ContextManager[pyarrow.Table]:
    """
    Load `parquet_path` as a low-RAM (mmapped) pyarrow.Table.

    Raise `pyarrow.ArrowIOError` on invalid input file.

    Dictionary-encoded columns will stay dictionary-encoded. Practically,
    `parquet.write(path, table); table = parquet.read(path)` does not change
    `table`.
    """
    with tempfile_context() as arrow_path:
        # raise ArrowIOError
        convert_parquet_file_to_arrow_file(parquet_path, arrow_path)
        reader = pyarrow.ipc.open_file(str(arrow_path))
        arrow_table = reader.read_all()
        yield arrow_table


def read(parquet_path: Path) -> pyarrow.Table:
    """
    Return a pyarrow.Table, with its backing file deleted.

    (Even though the file is deleted from the _filesystem_, the data is still
    on disk and mmapped until the return value goes out of scope.)
    """
    with open_as_mmapped_arrow(parquet_path) as table:
        return table


def _read_pylist(column: pyarrow.ChunkedArray) -> List[Any]:
    dtype = column.type

    pylist = column.to_pylist()
    if pyarrow.types.is_timestamp(dtype) and dtype.unit == "ns":
        # pyarrow returns timestamps as pandas.Timestamp values (because
        # that has higher resolution than datetime.datetime). But we want
        # datetime.datetime. We'll truncate to microseconds.
        #
        # If someone complains, then we should change our API to pass int64
        # instead of datetime.datetime.
        pylist = [None if v is None else v.to_pydatetime(warn=False) for v in pylist]
    return pylist


def read_pydict(
    parquet_path: Path, only_columns: range, only_rows: range
) -> Dict[str, List[Any]]:
    """
    Return a dict mapping column name to data (Python objects).

    Raise pyarrow.ArrowIOError if processing fails.

    Python data consumes RAM, so the caller must specify columns and rows.
    Specify them with integer keys.

    `retval.keys()` is in table-column order (not `only_columns` order).

    Missing rows and columns are ignored.

    `NaN` is returned as `float("nan")`, but `None` is returned as `None`.
    Caller beware: a Parquet column can contain both!
    """
    assert only_columns.step == 1
    assert only_columns.start >= 0
    assert only_columns.stop >= only_columns.start
    assert only_rows.step == 1
    assert only_rows.start >= 0
    assert only_rows.stop >= only_rows.start

    with tempfile_context(prefix="read_pydict-", suffix=".arrow") as arrow_path:
        try:
            subprocess.check_output(
                [
                    "/usr/bin/parquet-to-arrow-slice",
                    str(parquet_path),
                    "%d-%d" % (only_columns.start, only_columns.stop),
                    "%d-%d" % (only_rows.start, only_rows.stop),
                    str(arrow_path),
                ]
            )
        except subprocess.CalledProcessError as err:
            raise pyarrow.ArrowIOError(
                "Conversion failed with status %d: %s"
                % (
                    err.returncode,
                    (err.output or b"").decode("utf-8", errors="replace"),
                )
            )

        reader = pyarrow.ipc.open_file(str(arrow_path))
        table = reader.read_all()
        return {
            name: _read_pylist(chunks)
            for name, chunks in zip(table.column_names, table.columns)
        }
