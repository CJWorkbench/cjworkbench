from pathlib import Path
import fastparquet
from fastparquet import ParquetFile
import pandas
import snappy
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


class FastparquetCouldNotHandleFile(Exception):
    pass


class FastparquetIssue361(FastparquetCouldNotHandleFile):
    """
    The file has zero columns and Fastparquet has a bug.

    https://github.com/dask/fastparquet/issues/361 -- TODO upgrade
    fastparquet and nix this error.
    """
    pass


class FastparquetIssue375(FastparquetCouldNotHandleFile):
    """
    The file was written by pyarrow, has a really long string and
    Fastparquet has a bug.

    Track the issue at https://github.com/dask/fastparquet/issues/375
    """
    pass


def read_header(path: Path) -> ParquetFile:
    """
    Ensure a ParquetFile exists, and return it with headers read.

    May raise OSError (e.g., FileNotFoundError) or
    FastparquetCouldNotHandleFile.

    `retval.fn` gives the filename; `retval.columns` gives column names;
    `retval.dtypes` gives pandas dtypes, and `retval.to_pandas()` reads
    the entire file.
    """
    try:
        return fastparquet.ParquetFile(path)
    except IndexError:
        # TODO nix this when fastparquet resolves
        # https://github.com/dask/fastparquet/issues/361
        #
        # The file has a zero-length column list, and fastparquet can't
        # handle that.
        #
        # Our cached DataFrame should be "empty". No columns means no
        # rows.
        raise FastparquetIssue361


def read(path: Path) -> pandas.DataFrame:
    """
    Load a Pandas DataFrame from disk or raise FileNotFoundError or
    FastparquetCouldNotHandleFile.

    May raise OSError (e.g., FileNotFoundError) or
    FastparquetCouldNotHandleFile. The latter comes from
    https://github.com/dask/fastparquet/issues/375 -- we used to write with
    pyarrow, and fastparquet fails on some files with large strings. Those
    files are so old we won't attempt to support them.
    """
    try:
        pf = read_header(path)
        return pf.to_pandas()  # no need to close? Weird API
    except snappy.UncompressError as err:
        if str(err) == 'Error while decompressing: invalid input':
            # Assume Fastparquet is reporting the wrong bug.
            #
            # XXX this means we can't actually report corrupt files. Let's fix
            # Fastparquet and delete this possibility altogether.
            raise FastparquetIssue375
        raise
    except AssertionError:
        raise FastparquetIssue375


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
