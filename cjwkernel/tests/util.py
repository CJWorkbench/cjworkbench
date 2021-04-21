import io
import pathlib
import unittest
import unittest.mock
from contextlib import contextmanager
from typing import Any, ContextManager, Dict, Iterable, List, Optional, Tuple, Union

import pyarrow
import pyarrow.parquet
from cjwmodule.arrow.testing import make_table

from cjwkernel import settings
from cjwkernel.util import tempfile_context


__all__ = [
    "MockDir",
    "MockPath",
    "arrow_table_context",
    "override_settings",
    "parquet_file",
]


@contextmanager
def arrow_table_context(
    *columns,
    dir: Optional[pathlib.Path] = None,
) -> ContextManager[Tuple[pathlib.Path, pyarrow.Table]]:
    """Yield a Path and a pa.Table with its contents.

    Two calling conventions:

        with arrow_table_context(make_column("A", [1]), make_column("B", [2])) as (path, table):
            pass

        table = make_table(make_column("A", [1]), make_column("B", [1]))
        with arrow_table_context(x) as (path, _):
            pass
    """
    if len(columns) == 1 and isinstance(columns[0], pyarrow.Table):
        table = columns[0]
    else:
        table = make_table(*columns)

    with tempfile_context(dir=dir) as path:
        writer = pyarrow.RecordBatchFileWriter(path, table.schema)
        writer.write_table(table)
        writer.close()
        yield path, table


@contextmanager
def parquet_file(
    table: Union[Dict[str, List[Any]], pyarrow.Table],
    dir: Optional[pathlib.Path] = None,
) -> ContextManager[pathlib.Path]:
    """Yield a filename with `table` written to a Parquet file."""
    if isinstance(table, dict):
        table = pyarrow.table(table)

    with tempfile_context(dir=dir) as parquet_path:
        pyarrow.parquet.write_table(
            table,
            parquet_path,
            version="2.0",
            compression="SNAPPY",
            use_dictionary=[
                name.encode("utf-8")
                for name, column in zip(table.column_names, table.columns)
                if pyarrow.types.is_dictionary(column.type)
            ],
        )
        yield parquet_path


def override_settings(**kwargs):
    return unittest.mock.patch.multiple(settings, **kwargs)


class MockPath(pathlib.PurePosixPath):
    """
    Simulate pathlib.Path

    Features:

        * read_bytes()
        * read_text(), including encoding and errors
        * open()
        * when `data` is None, raise `FileNotFoundError` when expecting a file
    """

    def __new__(
        cls,
        parts: List[str],
        data: Optional[bytes],
        parent: Optional[pathlib.PurePosixPath] = None,
    ):
        ret = super().__new__(cls, *parts)
        ret.data = data
        ret._parent = parent
        return ret

    # override
    @property
    def parent(self):
        return self._parent

    # Path interface
    def read_bytes(self):
        if self.data is None:
            raise FileNotFoundError(self.name)

        return self.data

    # Path interface
    def read_text(self, encoding="utf-8", errors="strict"):
        if self.data is None:
            raise FileNotFoundError(self.name)

        return self.data.decode(encoding, errors)

    def open(self, mode):
        assert mode == "rb"
        return io.BytesIO(self.data)


class MockDir(pathlib.PurePosixPath):
    """
    Mock filesystem directory using pathlib.Path interface.

    Usage:

        dirpath: PurePath = MockDir({
            'yyy/xxx.yaml': b'id_name: xxx...'
            'xxx.py': b'def render(
        })

        yaml_text = (dirpath / 'yyy' / 'xxx.yaml').read_text()
    """

    def __new__(
        cls,
        filedata: Dict[str, bytes],
        parent: pathlib.PurePath = pathlib.PurePath("/"),
        basename: str = "root",
    ):  # filename => bytes
        ret = super().__new__(cls, parent, basename)

        ret._filenames = list(filedata.keys())
        ret._children = {}
        ret._parent = parent
        subfolders = {}
        for filename, data in filedata.items():
            if "/" in filename:
                subfolder, subpath = filename.split("/", 1)
                if not subfolder in subfolders:
                    subfolders[subfolder] = {}
                subfolders[subfolder][subpath] = data
            else:
                ret._children[filename] = MockPath(
                    [ret.as_posix(), filename], parent=ret, data=data
                )
        for subfolder, subfolder_data in subfolders.items():
            ret._children[subfolder] = MockDir(
                subfolder_data, parent=ret, basename=subfolder
            )
        return ret

    # override
    @property
    def parent(self):
        return self._parent

    # override
    def __truediv__(self, filename: str) -> MockPath:
        try:
            if "/" in filename:
                subfolder, subpath = filename.split("/", 1)
                return self._children[subfolder] / subpath
            else:
                return self._children[filename]
        except KeyError:
            return MockPath([self.as_posix(), filename], data=None, parent=self)

    def glob(self, pattern: str) -> Iterable[MockPath]:
        for filename in self._filenames:
            path = self / filename
            if path.match(pattern):
                yield path
