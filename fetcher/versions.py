import errno
import io
from pathlib import Path
from cjwkernel import parquet
from cjwkernel.types import FetchResult


_BUFFER_SIZE = 1024 * 1024


_is_parquet_path = parquet.file_has_parquet_magic_number


def _are_file_contents_equal(path1: Path, path2: Path) -> bool:
    """
    Return whether both paths are byte-for-byte equal.

    Raise OSError if file read fails
    """
    # Don't use `filecmp`: it has a _cache global variable; and the underlying
    # loop is simple enough to transcribe.
    buffer1 = bytearray(_BUFFER_SIZE)
    buffer2 = bytearray(_BUFFER_SIZE)
    with path1.open("rb", buffering=_BUFFER_SIZE) as f1:
        with path2.open("rb", buffering=_BUFFER_SIZE) as f2:
            while True:
                n1 = f1.readinto(buffer1)
                n2 = f2.readinto(buffer2)
                if n1 != n2 or buffer1[:n1] != buffer2[:n2]:
                    return False
                if not n1:
                    return True


def are_fetch_results_equal(new_result: FetchResult, old_result: FetchResult) -> bool:
    """
    Determine whether `new_result` is worth saving in the database.

    [adamhooper, 2019-10-28] *my* dream is: each fetch should create a version;
    and the module can declare, "this version is an exact copy of the previous
    version."

    Why don't we have this? Because we haven't defined "version". There are two
    good definitions:

    1. A "version" is the result of a fetch (i.e., "new JSON from the server")
    2. A "version" is the result of a render (i.e., "tweet data changed")

    I think the intuitive definition is 2. But we don't use 2, because we never
    designed it. There's no UX for a user to see three versions of the output
    of step 5, and that's hard: we need to help the user distinguish "I changed
    a previous step's params" from "data from the server changed". And
    code-wise... there's no code for this because there's no design. Nothing
    strikes me as a clever architecture that would nudge us towards a certain
    design: it seems to me this is going to be hard, no matter what.

    After we've defined "version" correctly, _then_ we're going to want to
    store every fetch result in the database.

    ... Back to reality. For now, "version" is a fetch result we've bothered to
    save. Basically, we _guess_ whether the render result given `new_result` as
    input will be the same as the render result given `old_result` as input.

    Heuristics:

        1. If errors are different, the results are different.
        2. If the render result is a Parquet file (legacy fetch retval),
           compare schemas and values in the two Parquet files; return the
           result.
        3. Otherwise, compare file contents of the two files on disk; return
           the result.
    """
    if new_result.errors != old_result.errors:
        return False

    if _is_parquet_path(old_result.path) and _is_parquet_path(new_result.path):
        return parquet.are_files_equal(old_result.path, new_result.path)
    else:
        return _are_file_contents_equal(old_result.path, new_result.path)
