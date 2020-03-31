import tempfile
from pathlib import Path

from cjwparse.api import parse_csv


def render(arrow_table, params, output_path, *, settings, **kwargs):
    with tempfile.NamedTemporaryFile(suffix=".txt") as tf:
        utf8_path = Path(tf.name)
        utf8_path.write_text(params["csv"], encoding="utf-8")

        return parse_csv(
            utf8_path,
            output_path=output_path,
            encoding="utf-8",
            delimiter=None,
            has_header=params["has_header_row"],
            autoconvert_text_to_numbers=True,
            settings=settings,
        )
