from cjwkernel.pandas.parse import parse_csv
from cjwkernel.util import tempfile_context


def render_arrow(table, params, tab_name, fetch_result, output_path):
    with tempfile_context(suffix=".txt") as utf8_path:
        utf8_path.write_text(params["csv"])

        return parse_csv(
            utf8_path,
            output_path=output_path,
            encoding="utf-8",
            delimiter=None,
            has_header=params["has_header_row"],
            autoconvert_text_to_numbers=True,
        )
