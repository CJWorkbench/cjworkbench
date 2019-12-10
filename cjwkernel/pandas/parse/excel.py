from pathlib import Path
import re
from typing import Any, List
import pandas as pd
import xlrd
from cjwkernel.types import I18nMessage, RenderError, RenderResult
from cjwkernel import settings
from ..types import ProcessResult
from ..moduleutils import autocast_dtypes_in_place


_PATTERN_CONTROL_CHARACTERS = re.compile("[\x00-\x1f]")


def _uniquify(colnames: List[str]) -> List[str]:
    """
    Return `colnames`, renaming non-unique names to be unique.

    The logic: walk the list from left to right. When we see a column name,
    for the first time, blacklist it. If we see a blacklisted column name,
    rename it by adding a unique digit and blacklist the new name.
    """
    seen = set()
    ret = []

    for colname in colnames:
        if colname in seen:
            # Modify `colname` by adding a number to it.
            for n in itertools.count():
                try_colname = f"{colname} {n + 1}"
                if try_colname not in seen:
                    colname = try_colname
                    break
        ret.append(colname)
        seen.add(colname)

    return ret


def _truncate_string_to_max_bytes(s: str, max_bytes: int):
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s

    while True:
        b = b[:max_bytes]
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            # We nixed a continuation byte. Nix more bytes until we fit.
            max_bytes -= 1


def _clean_column_name(colname: Any, index: int) -> str:
    # Convert to string! Pandas can produce non-string colnames.
    colname = str(colname)

    # Strip control characters
    colname = _PATTERN_CONTROL_CHARACTERS.sub("", colname)

    # Reduce number of characters -- adding a 4-byte buffer for
    # uniquify_colnames().
    colname = _truncate_string_to_max_bytes(
        colname, settings.MAX_BYTES_PER_COLUMN_NAME - 4
    )

    # Do not allow empty-string column name
    if not colname:
        colname = f"Column {index + 1}"

    return colname


def parse_xls_file(
    path: Path, *, output_path: Path, has_header: bool, autoconvert_types: bool
) -> RenderResult:
    """
    Build a RenderResult from xlsx bytes or raise parse error.

    Peculiarities:

    * Error can be xlrd.XLRDError or pandas error
    * We read the entire file contents into memory before parsing
    """
    # Use xlrd.open_workbook(): if we call pandas.read_excel(bytesio) it
    # will read the entire file into RAM.

    # dtype='category' crashes as of 2018-09-11
    try:
        workbook = xlrd.open_workbook(path.as_posix())
        table = pd.read_excel(
            workbook, engine="xlrd", dtype=object, header=(0 if has_header else None)
        )
    except xlrd.XLRDError as err:
        return RenderResult(
            errors=[
                RenderError(
                    I18nMessage.TODO_i18n(f"Error reading Excel file: %s" % str(err))
                )
            ]
        )

    if has_header:
        # pd.read_excel() _badly_ uniquifies column names: it adds ".1", ".2",
        # etc. This is hard to fix. We'd need to stop using pd.read_excel().
        # [2019-12-09, adamhooper] Not today.
        #
        # We still need to call _uniquify(), because _clean_column_name() can
        # map different strings to the same string.
        table.columns = _uniquify(
            [_clean_column_name(c, i) for i, c in enumerate(table.columns)]
        )
    else:
        table.columns = [f"Column {i + 1}" for i in range(len(table.columns))]

    autocast_dtypes_in_place(table)

    return ProcessResult(table).to_arrow(output_path)


parse_xlsx_file = parse_xls_file
