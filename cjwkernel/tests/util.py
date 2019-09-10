from contextlib import contextmanager
from pathlib import Path
import os
import tempfile
from typing import Any, Dict, List, Optional, Union
import unittest
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, TableMetadata, Column, ColumnType, RenderResult


@contextmanager
def arrow_file(table: Union[Dict[str, List[Any]], pyarrow.Table]):
    """
    Yield a filename with `table` written to an Arrow file.
    """
    if isinstance(table, dict):
        table = pyarrow.Table.from_pydict(table)

    fd, filename = tempfile.mkstemp()
    try:
        os.close(fd)
        writer = pyarrow.RecordBatchFileWriter(filename, table.schema)
        writer.write_table(table)
        writer.close()
        yield filename
    finally:
        try:
            os.unlink(filename)
        except FileNotFoundError:
            pass


def _arrow_column_to_column(column: pyarrow.Column) -> Column:
    if pyarrow.types.is_floating(column.type) or pyarrow.types.is_integer(column.type):
        column_type = ColumnType.Number("{:,}")
    elif pyarrow.types.is_timestamp(column.type):
        column_type = ColumnType.DateTime()
    elif pyarrow.types.is_string(column.type) or pyarrow.types.is_dictionary(
        column.type
    ):
        column_type = ColumnType.Text()
    return Column(column.name, column_type)


@contextmanager
def arrow_table_context(
    table: Union[Dict[str, List[Any]], pyarrow.Table],
    columns: Optional[List[Column]] = None,
):
    """
    Yield an ArrowTable (whose `.path` is a file).

    Metadata is inferred. Number columns have format `{:,}`.
    """
    if isinstance(table, dict):
        table = pyarrow.Table.from_pydict(table)

    if columns is None:
        columns = [_arrow_column_to_column(c) for c in table.columns]
    metadata = TableMetadata(table.num_rows, columns)

    with arrow_file(table) as filename:
        yield ArrowTable(Path(filename), metadata)


def arrow_table(
    table: Union[Dict[str, List[Any]], pyarrow.Table],
    columns: Optional[List[Column]] = None,
) -> ArrowTable:
    """
    Yield an ArrowTable (whose `.path` is a _deleted_ file).

    Metadata is inferred. Number columns have format `{:,}`.

    The path may be deleted, but the file on disk is still mmapped.
    """
    with arrow_table_context(table, columns) as table:
        return table


def assert_arrow_table_equals(result1: ArrowTable, result2: ArrowTable):
    assertEqual = unittest.TestCase().assertEqual
    assertEqual(result1.metadata, result2.metadata)
    if result1.table is not None and result2.table is not None:
        assertEqual(result1.table.to_pydict(), result2.table.to_pydict())
    else:
        assertEqual(result1.table is None, result2.table is None)


def assert_render_result_equals(result1: RenderResult, result2: RenderResult):
    assert_arrow_table_equals(result1.table, result2.table)
    assertEqual = unittest.TestCase().assertEqual
    assertEqual(
        [e.to_dict() for e in result1.errors], [e.to_dict() for e in result2.errors]
    )
    assertEqual(result1.json, result2.json)


def override_settings(**kwargs):
    return unittest.mock.patch.multiple(settings, **kwargs)
