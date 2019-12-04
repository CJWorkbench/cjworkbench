from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Optional
import pyarrow
from cjwkernel import settings
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult
from cjwkernel.util import tempfile_context
from .postprocess import dictionary_encode_columns, infer_table_metadata
from .text import transcode_to_utf8_and_warn


class ParseJsonWarning:
    pass


@dataclass(frozen=True)
class ParseJsonWarningRepairedEncoding(ParseJsonWarning):
    encoding: str
    first_invalid_byte: int
    first_invalid_byte_position: int

    def __str__(self):  # TODO nix when we support i18n
        return (
            "Encoding error: byte 0x%02X is invalid %s at byte %d. "
            "We replaced invalid bytes with “�”."
        ) % (self.first_invalid_byte, self.encoding, self.first_invalid_byte_position)


@dataclass(frozen=True)
class ParseJsonWarningTODO_i18n:
    text: str

    def __str__(self):  # TODO nix when we support i18n
        return self.text


ParseJsonWarning.RepairedEncoding = ParseJsonWarningRepairedEncoding
ParseJsonWarning.TODO_i18n = ParseJsonWarningTODO_i18n


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
class ParseJsonResult:
    table: pyarrow.Table
    warnings: List[ParseJsonWarning]


def _parse_json(path: Path, *, encoding: Optional[str]) -> ParseJsonResult:
    """
    Parse JSON text file.

    Raise LookupError for an `encoding` Python cannot handle.

    Raise UnicodeError when the file simply cannot be read as text. (e.g., a
    UTF-16 file that does not start with a byte-order marker.)

    The process:

    1. Convert the file to UTF-8.
    2. Run `json-to-arrow` to parse the JSON into columns.
    3. Dictionary-encode each column if it's helpful.
    4. Write the final Arrow file.
    """
    warnings = []

    with tempfile_context(prefix="utf8-", suffix=".txt") as utf8_path:
        # raises LookupError, UnicodeError
        transcode_warning = transcode_to_utf8_and_warn(path, utf8_path, encoding)
        if transcode_warning is not None:
            warnings.append(
                ParseJsonWarning.RepairedEncoding(
                    encoding=transcode_warning.encoding,
                    first_invalid_byte=transcode_warning.first_invalid_byte,
                    first_invalid_byte_position=transcode_warning.first_invalid_byte_position,
                )
            )

        with tempfile_context(suffix=".arrow") as arrow_path:
            # raise subprocess.CalledProcessError on error ... but there is no
            # error json-to-arrow will throw that we can recover from.
            child = subprocess.run(
                [
                    "/usr/bin/json-to-arrow",
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
                    utf8_path.as_posix(),
                    arrow_path.as_posix(),
                ],
                capture_output=True,
                check=True,
            )
            if child.stdout:
                warnings.extend(
                    [
                        ParseJsonWarning.TODO_i18n(line)
                        for line in child.stdout.decode("utf-8").split("\n")
                        if line
                    ]
                )

            reader = pyarrow.ipc.open_file(arrow_path.as_posix())
            raw_table = reader.read_all()  # efficient -- RAM is mmapped

    table = _postprocess_table(raw_table)
    return ParseJsonResult(table, warnings)


def parse_json(
    path: Path, *, output_path: Path, encoding: Optional[str]
) -> RenderResult:
    result = _parse_json(path, encoding=encoding)
    with pyarrow.ipc.RecordBatchFileWriter(
        output_path.as_posix(), schema=result.table.schema
    ) as writer:
        writer.write_table(result.table)

    metadata = infer_table_metadata(result.table)

    arrow_table = ArrowTable(output_path, metadata)
    if result.warnings:
        # TODO when we support i18n, this will be even simpler....
        en_message = "\n".join([str(warning) for warning in result.warnings])
        errors = [RenderError(I18nMessage.TODO_i18n(en_message))]
    else:
        errors = []

    return RenderResult(arrow_table, errors)
