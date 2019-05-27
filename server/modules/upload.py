from .parse_util import parse_file


def render(table, params):
    if not params['file']:
        return table  # user hasn't uploaded yet

    return parse_file(params['file'], params['has_header'])
