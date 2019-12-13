from enum import Enum


class MimeType(Enum):
    CSV = "text/csv"
    TSV = "text/tab-separated-values"
    TXT = "text/plain"
    JSON = "application/json"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def from_extension(cls, ext: str):
        """
        Find MIME type by extension (e.g., ".txt").

        Raise KeyError if there is none.
        """
        return {
            ".csv": MimeType.CSV,
            ".tsv": MimeType.TSV,
            ".txt": MimeType.TXT,
            ".xls": MimeType.XLS,
            ".xlsx": MimeType.XLSX,
            ".json": MimeType.JSON,
        }[ext]
