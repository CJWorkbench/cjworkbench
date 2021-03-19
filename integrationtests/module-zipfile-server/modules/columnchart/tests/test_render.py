from collections import namedtuple

import numpy as np
import pandas as pd
from cjwmodule.testing.i18n import i18n_message

from columnchart import MaxNBars, render

DefaultParams = {
    "title": "",
    "x_axis_label": "",
    "y_axis_label": "",
    "x_column": "",
    "y_columns": [],
}


Column = namedtuple("Column", ("name", "type", "format"))


def P(**kwargs):
    """Easily build params, falling back to defaults."""
    assert not (set(kwargs.keys()) - set(DefaultParams.keys()))
    return {
        **DefaultParams,
        **kwargs,
    }


def test_happy_path():
    dataframe, error, json_dict = render(
        pd.DataFrame(
            {
                "A": ["foo", "bar"],
                "B": [1, 2],
                "C": [2, 3],
            }
        ),
        P(
            x_column="A",
            y_columns=[
                {"column": "B", "color": "#bbbbbb"},
                {"column": "C", "color": "#cccccc"},
            ],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
            "C": Column("C", "number", "{:,f}"),
        },
    )
    # Check values
    assert json_dict["data"]["values"] == [
        dict(x="foo", y0=1, y1=2),
        dict(x="bar", y0=2, y1=3),
    ]
    assert json_dict["transform"][1]["from"]["data"]["values"] == [
        dict(key="y0", series="B"),
        dict(key="y1", series="C"),
    ]
    # Check axis format is first Y column's format
    assert json_dict["config"]["axisY"]["format"] == ",r"


def test_output_nulls():
    dataframe, error, json_dict = render(
        pd.DataFrame(
            {
                "A": ["foo", "bar", None],
                "B": [np.nan, 2, 3],
                "C": [2, 3, 4],
            }
        ),
        P(
            x_column="A",
            y_columns=[
                {"column": "B", "color": "#bbbbbb"},
                {"column": "C", "color": "#cccccc"},
            ],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
            "C": Column("C", "number", "{:,f}"),
        },
    )
    # Check values
    assert json_dict["data"]["values"] == [
        dict(x="foo", y0=None, y1=2),
        dict(x="bar", y0=2, y1=3),
        # None row is removed
    ]


def test_x_column_missing():
    _, error, json_dict = render(
        pd.DataFrame(
            {
                "A": ["foo", "bar", None],
                "B": [np.nan, 2, 3],
            }
        ),
        P(
            x_column="",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    assert error == i18n_message("noXAxisError.message")
    assert set(json_dict.keys()) == {"error"}


def test_y_columns_missing():
    _, error, json_dict = render(
        pd.DataFrame(
            {
                "A": ["foo", "bar", None],
                "B": [np.nan, 2, 3],
            }
        ),
        P(
            x_column="A",
            y_columns=[],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    assert error == i18n_message("noYAxisError.message")
    assert set(json_dict.keys()) == {"error"}


def test_no_rows():
    _, error, json_dict = render(
        pd.DataFrame(
            {
                "A": pd.Series([], dtype=str),
                "B": pd.Series([], dtype=np.int32),
            }
        ),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    assert error == i18n_message("nothingToPlotError.message")
    assert set(json_dict.keys()) == {"error"}


def test_no_rows_with_non_null_x():
    _, error, json_dict = render(
        pd.DataFrame(
            {
                "A": pd.Series([None], dtype=str),
                "B": [1],
            }
        ),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    assert error == i18n_message("nothingToPlotError.message")
    assert set(json_dict.keys()) == {"error"}


def test_nix_null_x():
    _, __, json_dict = render(
        pd.DataFrame(
            {
                "A": [None, None, "a", None],
                "B": [1, 2, 3, 4],
            }
        ),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    # None row is removed
    assert json_dict["data"]["values"] == [dict(x="a", y0=3)]


def test_too_many_bars():
    _, error, json_dict = render(
        pd.DataFrame(
            {
                "A": [f"a{i}" for i in range(MaxNBars + 1)],
                "B": list(range(MaxNBars + 1)),
            }
        ),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{:,}"),
        },
    )
    assert error == i18n_message("tooManyBarsError.message", {"MaxNBars": MaxNBars})
    assert set(json_dict.keys()) == {"error"}


def test_x_axis_default_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1]}),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
        },
    )
    assert json_dict["encoding"]["x"]["title"] == "A"


def test_x_axis_custom_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1]}),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
            x_axis_label="New label",
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
        },
    )
    assert json_dict["encoding"]["x"]["title"] == "New label"


def test_y_axis_default_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1], "C": [2]}),
        P(
            x_column="A",
            y_columns=[
                {"column": "B", "color": "#bbbbbb"},
                {"column": "C", "color": "#cccccc"},
            ],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
            "C": Column("C", "number", "{,r}"),
        },
    )
    assert json_dict["layer"][0]["encoding"]["y"]["title"] == "B"


def test_y_axis_custom_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1], "C": [2]}),
        P(
            x_column="A",
            y_columns=[
                {"column": "B", "color": "#bbbbbb"},
                {"column": "C", "color": "#cccccc"},
            ],
            y_axis_label="New label",
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
            "C": Column("C", "number", "{,r}"),
        },
    )
    assert json_dict["layer"][0]["encoding"]["y"]["title"] == "New label"


def test_default_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1]}),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
        },
    )
    assert json_dict["title"] == ""


def test_custom_title():
    _, __, json_dict = render(
        pd.DataFrame({"A": ["a"], "B": [1]}),
        P(
            x_column="A",
            y_columns=[{"column": "B", "color": "#bbbbbb"}],
            title="New label",
        ),
        input_columns={
            "A": Column("A", "text", None),
            "B": Column("B", "number", "{,r}"),
        },
    )
    assert json_dict["title"] == "New label"
