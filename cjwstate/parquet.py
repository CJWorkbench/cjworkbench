import contextlib
import fastparquet
from pathlib import Path
import tempfile
from typing import ContextManager, List, Optional
import pyarrow.parquet


def convert_parquet_file_to_arrow_file(
    parquet_path: Path,
    arrow_path: Path,
    only_columns: Optional[List[str]] = None,
    only_rows: Optional[range] = None,
) -> None:
    if only_rows is not None:
        assert only_rows.step == 1 and only_rows.start <= only_rows.stop

    # TODO stream one column at a time? pyarrow makes it tricky, but it would
    # be more efficient because less RAM would be used.

    # we use fastparquet, not pyarrow, to read metadata: [2019-09-15] pyarrow.parquet
    # doesn't treat dictionary-encoded columns as dictionary-encoded (and it
    # seems impossible to detect dictionary encoding). TODO pyarrow v0.15.0,
    # we should use `pyarrow.parquet.read_table(..., use_categories=...)`.
    fastparquet_file = fastparquet.ParquetFile(str(parquet_path))
    # if len(fastparquet_file.row_groups) > 1:
    #     raise pyarrow.ArrowIOError("Workbench only supports 0 or 1 parquet row group")
    try:
        rg0_columns = fastparquet_file.row_groups[0].columns
        dictionary_columns = frozenset(
            c.meta_data.path_in_schema[0]
            for c in rg0_columns
            if c.meta_data.dictionary_page_offset is not None
        )
    except IndexError:  # there is no row group 0
        dictionary_columns = frozenset()

    parquet_file = pyarrow.parquet.ParquetFile(str(parquet_path))
    arrays: List[pyarrow.Array] = []
    names: List[str] = []
    for column in parquet_file.schema:
        if only_columns is not None and column.name not in only_columns:
            continue

        # TODO write in serial, so we don't store the whole Arrow table in RAM
        array = parquet_file.read(
            [column.name], use_threads=False, use_pandas_metadata=False
        )[0]
        if only_rows is not None:
            array = array[only_rows.start : only_rows.stop]
        if column.name in dictionary_columns:
            array = array.dictionary_encode()
        arrays.append(array)
        names.append(column.name)
    table = pyarrow.Table.from_arrays(arrays, names=names)

    # Be sure to ignore the parquet file's schema metadata, because it can
    # cause an error like this on Fastparquet-dumped files:
    #
    #   File "pyarrow/array.pxi", line 441, in pyarrow.lib._PandasConvertible.to_pandas
    #   File "pyarrow/table.pxi", line 1367, in pyarrow.lib.Table._to_pandas
    #   File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.7/site-packages/pyarrow/pandas_compat.py", line 644, in table_to_blockmanager
    #     table = _add_any_metadata(table, pandas_metadata)
    #   File "/root/.local/share/virtualenvs/app-4PlAip0Q/lib/python3.7/site-packages/pyarrow/pandas_compat.py", line 967, in _add_any_metadata
    #     idx = schema.get_field_index(raw_name)
    #   File "pyarrow/types.pxi", line 902, in pyarrow.lib.Schema.get_field_index
    #   File "stringsource", line 15, in string.from_py.__pyx_convert_string_from_py_std__in_string
    # TypeError: expected bytes, dict found
    #
    # [2019-08-22] fastparquet-dumped files will be around for a long time.
    #
    # We don't care about schema metadata, anyway. Workbench has its own
    # restrictive schema; we don't need extra Pandas-specific data because
    # we don't support everything Pandas supports.

    writer = pyarrow.RecordBatchFileWriter(str(arrow_path), table.schema)
    writer.write_table(table)
    writer.close()


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
        compression="SNAPPY",
        # Preserve whatever dictionaries we have in Pandas. Write+read
        # should return an exact copy.
        use_dictionary=[
            c.name.encode("utf-8")
            for c in table.columns
            if pyarrow.types.is_dictionary(c.type)
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
    with tempfile.NamedTemporaryFile() as tf:
        arrow_path = Path(tf.name)
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
