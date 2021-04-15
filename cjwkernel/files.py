from pathlib import Path
from typing import List, Optional

import cjwparquet
import pyarrow as pa

from .util import tempfile_context
from .types import Column, ColumnType


def _rewrite_field(field: pa.Field, column_type: ColumnType) -> pa.Field:
    if isinstance(column_type, ColumnType.Number):
        return pa.field(field.name, field.type, metadata={"format": column_type.format})
    if isinstance(column_type, ColumnType.Text):
        return pa.field(field.name, field.type, metadata=None)
    if isinstance(column_type, ColumnType.Timestamp):
        return pa.field(field.name, field.type, metadata=None)
    if isinstance(column_type, ColumnType.Date):
        return pa.field(field.name, field.type, metadata={"unit": column_type.unit})
    raise ValueError("Unknown column type %r" % column_type)


def _rewrite_schema(schema: pa.Schema, columns: List[Column]):
    return pa.schema(
        [
            _rewrite_field(schema.field(i), column.type)
            for i, column in enumerate(columns)
        ]
    )


def read_parquet_as_arrow(
    path: Path, columns: List[Column], tempdir: Optional[Path] = None
):
    """Read Parquet file as Arrow.

    The Arrow table will appear to be in-memory; but it will be backed by an
    mmapped-and-then-deleted temporary file in `tempdir`. It will cost virtual
    RAM; but it won't always consume physical RAM.

    Raise pyarrow.ArrowIOError on invalid Parquet file.
    """
    with tempfile_context(dir=tempdir) as typeless_arrow_path:
        cjwparquet.convert_parquet_file_to_arrow_file(path, typeless_arrow_path)

        with pa.ipc.open_file(typeless_arrow_path) as reader:
            typeless_schema = reader.schema
            typeless_table = reader.read_all()
            schema = _rewrite_schema(typeless_schema, columns)

            return pa.table(typeless_table.columns, schema=schema)
