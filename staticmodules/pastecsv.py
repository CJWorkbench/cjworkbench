import io
import pandas as pd
from cjwkernel.pandas.parse_util import parse_text


def render(table, params):
    csv = params["csv"]
    if not csv:
        return pd.DataFrame()

    return parse_text(io.StringIO(params["csv"]), "txt", params["has_header_row"])
