from cjwparse.api import parse_file


def render(arrow_table, params, output_path, **kwargs):
    return parse_file(
        params["file"], output_path=output_path, has_header=params["has_header"]
    )
