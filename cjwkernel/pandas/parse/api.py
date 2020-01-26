from pathlib import Path
from typing import Optional
from cjwkernel.types import I18nMessage, RenderError, RenderResult
from .csv import parse_csv
from .excel import parse_xls_file, parse_xlsx_file
from .json import parse_json
from .mime import MimeType


def parse_file(
    path: Path,
    *,
    output_path: Path,
    encoding: Optional[str] = None,
    mime_type: Optional[MimeType] = None,
    has_header: bool = True,
) -> RenderResult:
    if mime_type is None:
        ext = "".join(path.suffixes).lower()
        try:
            mime_type = MimeType.from_extension(ext)
        except KeyError:
            return RenderResult(
                errors=[
                    RenderError(
                        I18nMessage.trans(
                            "py.cjwkernel.pandas.parse.api.parse_file.UknownExtension",
                            default="Unknown file extension {ext}. Please try a different file.",
                            args={"ext": ext},
                        )
                    )
                ]
            )

    if mime_type in {MimeType.CSV, MimeType.TSV, MimeType.TXT}:
        delimiter: Optional[str] = {
            MimeType.CSV: ",",
            MimeType.TSV: "\t",
            MimeType.TXT: None,
        }[mime_type]
        return parse_csv(
            path,
            output_path=output_path,
            encoding=encoding,
            delimiter=delimiter,
            has_header=has_header,
            autoconvert_text_to_numbers=True,
        )
    elif mime_type == MimeType.JSON:
        return parse_json(path, output_path=output_path, encoding=encoding)
    elif mime_type == MimeType.XLS:
        return parse_xls_file(
            path, output_path=output_path, has_header=has_header, autoconvert_types=True
        )
    elif mime_type == MimeType.XLSX:
        return parse_xlsx_file(
            path, output_path=output_path, has_header=has_header, autoconvert_types=True
        )
    else:
        raise RuntimeError("Unhandled MIME type")
