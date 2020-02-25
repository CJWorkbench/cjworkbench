from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context
from .postprocess import dictionary_encode_columns, infer_table_metadata


@dataclass(frozen=True)
class ParseXlsxWarning:
    text: str

    def __str__(self):  # TODO nix when we support i18n
        return self.text


def _postprocess_table(table: pyarrow.Table) -> pyarrow.Table:
    """
    Transform `raw_table` to meet our standards:

    * Convert each column dictionary if it agrees with
      `settings.MAX_DICTIONARY_SIZE` and
      `settings.MIN_DICTIONARY_COMPRESSION_RATIO`.
    """
    table = dictionary_encode_columns(table)
    return table


@dataclass(frozen=True)
class ParseXlsxResult:
    table: pyarrow.Table
    warnings: List[ParseXlsxWarning]


def _parse_xlsx(path: Path, *, header_rows: str) -> ParseXlsxResult:
    """
    Parse Excel .xlsx file.

    The process:

    1. Run `xlsx-to-arrow` to parse cells into columns.
    2. Dictionary-encode each column if it's helpful.
    3. Write the final Arrow file.
    """
    warnings = []

    with tempfile_context(suffix=".arrow") as arrow_path:
        # raise subprocess.CalledProcessError on error ... but there is no
        # error json-to-arrow will throw that we can recover from.
        child = subprocess.run(
            [
                "/usr/bin/xlsx-to-arrow",
                "--max-rows",
                str(settings.MAX_ROWS_PER_TABLE),
                "--max-columns",
                str(settings.MAX_COLUMNS_PER_TABLE),
                "--max-bytes-per-value",
                str(settings.MAX_BYTES_PER_VALUE),
                "--max-bytes-total",
                str(settings.MAX_BYTES_TEXT_DATA),
                "--max-bytes-per-column-name",
                str(settings.MAX_BYTES_PER_COLUMN_NAME),
                "--header-rows",
                header_rows,
                path.as_posix(),
                arrow_path.as_posix(),
            ],
            capture_output=True,
            check=True,
        )
        if child.stdout:
            warnings.extend(
                [
                    ParseXlsxWarning(line)
                    for line in child.stdout.decode("utf-8").split("\n")
                    if line
                ]
            )

        reader = pyarrow.ipc.open_file(arrow_path.as_posix())
        raw_table = reader.read_all()  # efficient -- RAM is mmapped

    table = _postprocess_table(raw_table)
    return ParseXlsxResult(table, warnings)


def parse_xlsx(
    path: Path, *, output_path: Path, has_header: bool
) -> RenderResult:
    result = _parse_xlsx(path, header_rows=("0-1" if has_header else ""))
    with pyarrow.ipc.RecordBatchFileWriter(
        output_path.as_posix(), schema=result.table.schema
    ) as writer:
        writer.write_table(result.table)

    metadata = infer_table_metadata(result.table)

    if len(metadata.columns) == 0:
        arrow_table = ArrowTable()
    else:
        arrow_table = ArrowTable(output_path, result.table, metadata)
    if result.warnings:
        # TODO when we support i18n, this will be even simpler....
        en_message = "\n".join([str(warning) for warning in result.warnings])
        errors = [RenderError(I18nMessage.TODO_i18n(en_message))]
    else:
        errors = []

    return RenderResult(arrow_table, errors)
