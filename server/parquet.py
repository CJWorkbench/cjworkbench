from pathlib import Path
import fastparquet
import pandas
import warnings


# Suppress this arning:
# .../python3.6/site-packages/fastparquet/writer.py:407: FutureWarning: Method
# .valid will be removed in a future version. Use .dropna instead.
#   out = data.valid()  # better, data[data.notnull()], from above ?
#
# warnings.catch_warnings() is not thread-safe so we can't use it.
warnings.filterwarnings(
    action='ignore',
    message='Method .valid will be removed in a future version.',
    category=FutureWarning,
    module='fastparquet.writer'
)


def read(path: Path) -> pandas.DataFrame:
    """
    Load a Pandas DataFrame from disk or raise FileNotFoundError.
    """
    pf = fastparquet.ParquetFile(path)
    return pf.to_pandas()  # no need to close? Weird API


def write(path: Path, table: pandas.DataFrame) -> None:
    """
    Write a Pandas DataFrame to a file on disk, overwriting if needed.

    `path`'s directory must exist, and the user must have permission to write
    to `path`: otherwise, this function raises OSError.

    We aim to keep the file format "stable": all future versions of
    parquet.read() should support all files written by today's version of this
    function.
    """
    fastparquet.write(path, table, compression='SNAPPY',
                      object_encoding='utf8')
