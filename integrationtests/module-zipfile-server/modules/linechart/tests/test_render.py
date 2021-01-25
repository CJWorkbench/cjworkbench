import json
from collections import namedtuple

import pandas as pd
from cjwmodule.testing.i18n import i18n_message
from pandas.testing import assert_frame_equal

from linechart import render

Column = namedtuple("Column", ("name", "type", "format"))


def assertResult(result, expected):
    assert_frame_equal(result[0], expected[0])
    assert result[1] == expected[1]
    assert result[2] == expected[2]


def test_integration_empty_params():
    DefaultParams = {
        "title": "",
        "x_axis_label": "",
        "y_axis_label": "",
        "x_column": "",
        "y_columns": [],
    }
    table = pd.DataFrame({"A": [1, 2], "B": [2, 3]})
    result = render(
        table,
        DefaultParams,
        input_columns={
            "A": Column("A", "number", "{:,d}"),
            "B": Column("B", "number", "{:,.2f}"),
        },
    )
    assertResult(
        result,
        (
            table,
            i18n_message("noXAxisError.message"),
            {"error": "Please correct the error in this step's data or parameters"},
        ),
    )


def test_integration():
    table = pd.DataFrame({"A": [1, 2], "B": [2, 3]})
    result = render(
        table,
        {
            "title": "TITLE",
            "x_column": "A",
            "y_columns": [{"column": "B", "color": "#123456"}],
            "x_axis_label": "X LABEL",
            "y_axis_label": "Y LABEL",
        },
        input_columns={
            "A": Column("A", "number", "{:,d}"),
            "B": Column("B", "number", "{:,.2f}"),
        },
    )
    assert_frame_equal(result[0], table)
    assert result[1] == ""
    text = json.dumps(result[2])
    # We won't snapshot the chart: that's too brittle. (We change styling
    # more often than we change logic.) But let's make sure all our
    # parameters are in the JSON.
    assert '"TITLE"' in text
    assert '"X LABEL"' in text
    assert '"Y LABEL"' in text
    assert '"#123456"' in text
