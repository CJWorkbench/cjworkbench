import pyarrow
from cjwkernel import settings
from cjwkernel.types import Column, ColumnType, TableMetadata


def _string_array_pylist_n_bytes(data: pyarrow.ChunkedArray) -> int:
    text_buf = data.buffers()[-1]
    if text_buf is None:
        # All values are ""
        n_text_bytes = 0
    else:
        n_text_bytes = text_buf.size

    return (
        # 8 bytes per value (each value is a 64-bit pointer)
        (8 * len(data))
        # 50 bytes of overhead per string (heuristic) -- experiment with
        # sys.getsizeof() if you disbelieve.
        + (50 * (len(data) - data.null_count))
        # ... and then count the actual bytes of data
        + n_text_bytes
    )


def _maybe_dictionary_encode_column(data: pyarrow.ChunkedArray) -> pyarrow.ChunkedArray:
    if data.null_count == len(data):
        return data

    if data.chunk(0).offset > 0:
        # https://issues.apache.org/jira/browse/ARROW-7266#
        assert len(data.chunks) == 1
        data_copy = pyarrow.chunked_array(
            [pyarrow.serialize(data.chunk(0)).deserialize()]
        )
        encoded = data_copy.dictionary_encode()
    else:
        encoded = data.dictionary_encode()

    new_cost = _string_array_pylist_n_bytes(encoded.chunk(0).dictionary)

    if new_cost > settings.MAX_DICTIONARY_PYLIST_N_BYTES:
        # abort! abort! dictionary is too large
        return data

    old_cost = _string_array_pylist_n_bytes(data.chunk(0))

    if old_cost / new_cost >= settings.MIN_DICTIONARY_COMPRESSION_RATIO_PYLIST_N_BYTES:
        return encoded
    else:
        return data


def dictionary_encode_columns(table: pyarrow.Table) -> pyarrow.Table:
    return pyarrow.table(
        {
            name: (
                _maybe_dictionary_encode_column(column)
                if column.type == pyarrow.utf8()
                else column
            )
            for name, column in zip(table.column_names, table.columns)
        }
    )


def _infer_output_column_type(column: pyarrow.ChunkedArray) -> ColumnType:
    if pyarrow.types.is_string(column.type) or (
        hasattr(column.type, "value_type")
        and pyarrow.types.is_string(column.type.value_type)
    ):
        return ColumnType.Text()
    elif pyarrow.types.is_timestamp(column.type):
        return ColumnType.Datetime()
    else:
        return ColumnType.Number()


def infer_table_metadata(table: pyarrow.Table) -> TableMetadata:
    return TableMetadata(
        n_rows=table.num_rows,
        columns=[
            Column(name, _infer_output_column_type(column))
            for name, column in zip(table.column_names, table.columns)
        ],
    )
