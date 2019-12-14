from cjwkernel.pandas.parse import parse_file
from cjwkernel.types import RenderResult


def render_arrow(table, params, tab_name, fetch_result, output_path):
    if not params["file"]:
        return RenderResult()  # user hasn't uploaded yet

    return parse_file(
        params["file"], output_path=output_path, has_header=params["has_header"]
    )
