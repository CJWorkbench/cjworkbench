from __future__ import annotations

import json
from string import Formatter
from typing import Any, Dict, List, NamedTuple

import pandas as pd
from cjwmodule import i18n

MaxNBars = 500


def python_format_to_d3_tick_format(python_format: str) -> str:
    """
    Build a d3-scale tickFormat specification based on Python str.

    >>> python_format_to_d3_tick_format('{:,.2f}')
    ',.2f'
    >>> # d3-scale likes to mess about with precision. Its "r" format does
    >>> # what we want; if we left it blank, we'd see format(30) == '3e+1'.
    >>> python_format_to_d3_tick_format('{:,}')
    ',r'
    """
    # Formatter.parse() returns Iterable[(literal, field_name, format_spec,
    # conversion)]
    specifier = next(Formatter().parse(python_format))[2]
    if not specifier or specifier[-1] not in "bcdoxXneEfFgGn%":
        specifier += "r"
    return specifier


class GentleValueError(ValueError):
    """
    A ValueError that should not display in red to the user.

    The first argument must be an `i18n.I18nMessage`.

    On first load, we don't want to display an error, even though the user
    hasn't selected what to chart. So we'll display the error in the iframe:
    we'll be gentle with the user.
    """

    @property
    def i18n_message(self):
        return self.args[0]


class XSeries(NamedTuple):
    series: pd.Series

    @property
    def name(self):
        return self.series.name


class YSeries(NamedTuple):
    series: pd.Series
    color: str

    @property
    def name(self):
        return self.series.name


class SeriesParams(NamedTuple):
    """
    Fully-sane parameters. Columns are series.
    """

    title: str
    x_axis_label: str
    y_axis_label: str
    x_series: XSeries
    y_columns: List[YSeries]
    y_label_format: str

    def to_vega_data_values(self) -> List[Dict[str, Any]]:
        """
        Build an Array of Object records.

        Each record looks like {'x': 'foo', 'y0': 1, 'y1': 2.3, 'y2': null}.
        """
        df = pd.DataFrame(
            {
                "x": self.x_series.series,  # str or category
                # all the rest are number
                **{
                    f"y{i}": y_column.series
                    for i, y_column in enumerate(self.y_columns)
                },
            }
        )
        return [
            {k: None if pd.isnull(v) else v for k, v in record.items()}
            for record in df.to_dict(orient="records")
        ]

    def to_vega(self) -> Dict[str, Any]:
        """
        Build a Vega bar chart or grouped bar chart.
        """
        LABEL_COLOR = "#383838"
        TITLE_COLOR = "#686768"
        GRID_COLOR = "#ededed"
        n_bars = len(self.y_columns)
        ret = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": self.title,
            "config": {
                "font": "Roboto, Helvetica, sans-serif",
                "title": {
                    "offset": 15,
                    "color": LABEL_COLOR,
                    "fontSize": 20,
                    "fontWeight": "normal",
                },
                "axis": {
                    "gridColor": GRID_COLOR,
                    "labelColor": LABEL_COLOR,
                    "labelPadding": 10,
                    "labelFontSize": 12,
                    "labelFontWeight": "normal",
                    "titleColor": TITLE_COLOR,
                    "titleFontSize": 15,
                    "titleFontWeight": "normal",
                    "titlePadding": 15,
                },
                "axisX": {
                    "tickSize": 0,
                    "labelAngle": 0,
                    "labelFlush": True,
                    "labelAlign": "center",
                },
                "axisY": {
                    "format": self.y_label_format,
                    "tickColor": GRID_COLOR,  # fade into grid
                },
            },
            "data": {
                "values": self.to_vega_data_values(),
            },
            "transform": [
                {"fold": [f"y{i}" for i in range(n_bars)]},
                {
                    "lookup": "key",
                    "from": {
                        "data": {
                            "values": [
                                {"key": f"y{i}", "series": y_column.name}
                                for i, y_column in enumerate(self.y_columns)
                            ],
                        },
                        "key": "key",
                        "fields": ["series"],
                    },
                },
            ],
            "encoding": {
                "x": {
                    "field": "x",
                    "type": "nominal",
                    "scale": {
                        "padding": 0.25,  # relative width of gap between bars/groups
                    },
                    "title": self.x_axis_label,
                    "sort": None,
                },
                "color": {
                    "field": "series",
                    "scale": {
                        "range": [y_column.color for y_column in self.y_columns],
                    },
                },
                "tooltip": [
                    {"field": "x", "type": "nominal", "title": self.x_axis_label},
                    *[
                        {
                            "field": f"y{i}",
                            "type": "quantitative",
                            "title": y_column.name,
                        }
                        for i, y_column in enumerate(self.y_columns)
                    ],
                ],
            },
            "layer": [
                {
                    "mark": {
                        "type": "bar",
                        "width": {"expr": f'bandwidth("x") / {n_bars}'},
                        "xOffset": {
                            "expr": f'bandwidth("x") * (toNumber(slice(datum.key, 1)) - ({n_bars - 1} * 0.5)) / {n_bars}'
                        },
                    },
                    "encoding": {
                        "y": {
                            "field": "value",
                            "type": "quantitative",
                            "stack": None,
                            "title": self.y_axis_label,
                        },
                        "opacity": {
                            # When hovering over an X value, highlight its Y values
                            "condition": {
                                "test": {
                                    "param": "hover",
                                    "empty": True,
                                },
                                "value": 1,
                            },
                            "value": 0.7,
                        },
                    },
                },
                {
                    "mark": {
                        "type": "rule",
                        "opacity": 0,
                    },
                    "params": [
                        {
                            "name": "hover",
                            "select": {
                                "type": "point",
                                "encodings": ["x"],
                                "on": "mousemove",
                                "nearest": True,
                                "clear": "mouseout",
                                "toggle": False,
                            },
                        },
                    ],
                },
            ],
        }

        if self.y_label_format.endswith("d"):
            ret["config"]["axisY"]["tickMinStep"] = 1

        if len(self.y_columns) > 1:
            ret["encoding"]["color"]["legend"] = {
                "symbolType": "circle",
                "labelColor": LABEL_COLOR,
                "labelFontSize": 12,
                "labelFontWeight": "normal",
                "rowPadding": 10,
                "title": None,
            }
        else:
            ret["encoding"]["color"]["legend"] = None

        return ret


class YColumn(NamedTuple):
    column: str
    color: str


class Form(NamedTuple):
    """
    Parameter dict specified by the user: valid types, unchecked values.
    """

    title: str
    x_axis_label: str
    y_axis_label: str
    x_column: str
    y_columns: List[YColumn]

    @classmethod
    def from_params(cls, *, y_columns: List[Dict[str, str]], **kwargs) -> Form:
        return Form(**kwargs, y_columns=[YColumn(**y) for y in y_columns])

    def validate_with_table(
        self, table: pd.DataFrame, input_columns: Dict[str, Any]
    ) -> SeriesParams:
        """
        Create a SeriesParams ready for charting, or raises ValueError.

        Features ([tested?]):
        [x] Error if X column is missing
        [x] Error if no Y columns chosen
        [x] Error if no rows
        [x] Nix null X values
        [x] Error if too many bars
        [x] What if a Y column is not numeric? framework saves us
        [x] What if a Y column is the X column? framework saves us: x is text, y is numeric
        [x] Default title, X and Y axis labels
        """
        if not self.x_column:
            raise GentleValueError(
                i18n.trans("noXAxisError.message", "Please choose an X-axis column")
            )
        if not self.y_columns:
            raise GentleValueError(
                i18n.trans("noYAxisError.message", "Please choose a Y-axis column")
            )

        x_series_with_nulls = table[self.x_column]
        x_mask = ~(pd.isna(x_series_with_nulls))
        x_series = XSeries(
            pd.Series(x_series_with_nulls[x_mask], index=None, name=self.x_column)
        )

        if len(x_series.series) > MaxNBars:
            raise GentleValueError(
                i18n.trans(
                    "tooManyBarsError.message",
                    "Column chart can visualize a maximum of {MaxNBars} bars",
                    {"MaxNBars": MaxNBars},
                )
            )

        if not len(x_series.series):
            raise GentleValueError(
                i18n.trans("nothingToPlotError.message", "no records to plot")
            )

        y_columns = []
        for y_column in self.y_columns:
            y_series_with_nulls = table[y_column.column]
            y_series = pd.Series(
                y_series_with_nulls[x_mask], index=None, name=y_column.column
            )
            y_columns.append(YSeries(y_series, y_column.color))

        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name
        y_label_format = python_format_to_d3_tick_format(
            input_columns[y_columns[0].name].format
        )

        return SeriesParams(
            title=self.title,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            x_series=x_series,
            y_columns=y_columns,
            y_label_format=y_label_format,
        )


def _migrate_params_v0_to_v1(params):
    """
    v0: params['y_columns'] is JSON-encoded.

    v1: params['y_columns'] is List[Dict[{ name, color }, str]].
    """
    json_y_columns = params["y_columns"]
    if not json_y_columns:
        # empty str => no columns
        y_columns = []
    else:
        y_columns = json.loads(json_y_columns)
    return {**params, "y_columns": y_columns}


def migrate_params(params):
    if isinstance(params["y_columns"], str):
        params = _migrate_params_v0_to_v1(params)

    return params


def render(table, params, *, input_columns):
    form = Form.from_params(**params)
    try:
        valid_params = form.validate_with_table(table, input_columns)
    except GentleValueError as err:
        return (
            table,
            err.i18n_message,
            {
                "error": "Please correct the error in this step's data or parameters"
            },  # TODO_i18n
        )

    json_dict = valid_params.to_vega()
    return (table, "", json_dict)
