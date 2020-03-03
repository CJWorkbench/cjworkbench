from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Optional, Tuple
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context
from cjwmodule.util.colnames import gen_unique_clean_colnames_and_warn
import cjwmodule.i18n
from .postprocess import dictionary_encode_columns, infer_table_metadata


def _postprocess_table(
    table: pyarrow.Table, headers_table: Optional[pyarrow.Table]
) -> Tuple[pyarrow.Table, List[cjwmodule.i18n.I18nMessage]]:
    """
    Transform `raw_table` to meet our standards:

    * Convert each column dictionary if it agrees with
      `settings.MAX_DICTIONARY_SIZE` and
      `settings.MIN_DICTIONARY_COMPRESSION_RATIO`.
    * Rename columns if `headers_table` is provided.
    """
    table = dictionary_encode_columns(table)
    if headers_table is not None:
        colnames = [
            # filter out None and ""
            " - ".join(v for v in column.to_pylist() if v)
            for column in headers_table.itercolumns()
        ]
        colnames, warnings = gen_unique_clean_colnames_and_warn(
            colnames, settings=settings
        )
        table = table.rename_columns(colnames)
    else:
        warnings = []
    return table, warnings


@dataclass(frozen=True)
class ParseExcelResult:
    table: pyarrow.Table
    warnings: List[cjwmodule.i18n.I18nMessage]


def _parse_excel(tool: str, path: Path, *, header_rows: str) -> ParseExcelResult:
    """
    Parse Excel .xlsx or .xls file.

    The process:

    1. Run `/usr/bin/{tool}` (`xlsx-to-arrow`, say) to parse cells into columns.
    2. Dictionary-encode each column if it's helpful.
    3. Write the final Arrow file.
    """
    with tempfile_context(suffix=".arrow") as arrow_path, tempfile_context(
        suffix="-headers.arrow"
    ) as header_rows_path:
        # raise subprocess.CalledProcessError on error ... but there is no
        # error xls-to-arrow will throw that we can recover from.
        child = subprocess.run(
            [
                "/usr/bin/" + tool,
                "--max-rows",
                str(settings.MAX_ROWS_PER_TABLE),
                "--max-columns",
                str(settings.MAX_COLUMNS_PER_TABLE),
                "--max-bytes-per-value",
                str(settings.MAX_BYTES_PER_VALUE),
                "--max-bytes-total",
                str(settings.MAX_BYTES_TEXT_DATA),
                "--header-rows",
                header_rows,
                "--header-rows-file",
                header_rows_path.as_posix(),
                path.as_posix(),
                arrow_path.as_posix(),
            ],
            capture_output=True,
            check=True,
        )
        parse_warnings = [
            cjwmodule.i18n.I18nMessage("TODO_i18n", {"text": line}, None)
            for line in child.stdout.decode("utf-8").split("\n")
            if line
        ]

        with pyarrow.ipc.open_file(arrow_path.as_posix()) as reader:
            raw_table = reader.read_all()  # efficient -- RAM is mmapped
        if header_rows:
            with pyarrow.ipc.open_file(header_rows_path.as_posix()) as reader:
                maybe_headers_table = reader.read_all()
        else:
            maybe_headers_table = None

    table, colname_warnings = _postprocess_table(raw_table, maybe_headers_table)
    return ParseExcelResult(table, parse_warnings + colname_warnings)


def _write_parse_result_as_render_result(
    parse_result: ParseExcelResult, output_path: Path
) -> RenderResult:
    with pyarrow.ipc.RecordBatchFileWriter(
        output_path.as_posix(), schema=parse_result.table.schema
    ) as writer:
        writer.write_table(parse_result.table)

    metadata = infer_table_metadata(parse_result.table)

    if len(metadata.columns) == 0:
        arrow_table = ArrowTable()
    else:
        arrow_table = ArrowTable(output_path, parse_result.table, metadata)

    errors = [RenderError(I18nMessage(*warning)) for warning in parse_result.warnings]
    return RenderResult(arrow_table, errors)


def _parse_excel_and_write_result(
    *, tool: str, path: Path, output_path: Path, has_header: bool
) -> RenderResult:
    parse_result = _parse_excel(tool, path, header_rows=("0-1" if has_header else ""))
    return _write_parse_result_as_render_result(parse_result, output_path)


def parse_xlsx(path: Path, *, output_path: Path, has_header: bool) -> RenderResult:
    return _parse_excel_and_write_result(
        tool="xlsx-to-arrow", path=path, output_path=output_path, has_header=has_header
    )


def parse_xls(path: Path, *, output_path: Path, has_header: bool) -> RenderResult:
    return _parse_excel_and_write_result(
        tool="xls-to-arrow", path=path, output_path=output_path, has_header=has_header
    )
