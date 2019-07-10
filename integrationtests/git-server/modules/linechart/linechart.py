from __future__ import annotations
from dataclasses import dataclass
import json
from string import Formatter
from typing import Any, Dict, List
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_datetime64_dtype


MaxNAxisLabels = 300


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

    On first load, we don't want to display an error, even though the user
    hasn't selected what to chart. So we'll display the error in the iframe:
    we'll be gentle with the user.
    """


@dataclass
class XSeries:
    series: pd.Series
    column: Any
    """RenderColumn (has a '.name', '.type' and '.format')."""

    @property
    def name(self):
        return self.column.name

    @property
    def vega_data_type(self) -> str:
        if self.column.type == "datetime":
            return "temporal"
        elif self.column.type == "number":
            return "quantitative"
        else:  # text
            return "ordinal"

    @property
    def d3_tick_format(self) -> str:
        if self.column.type == "number":
            return python_format_to_d3_tick_format(self.column.format)
        else:
            return None

    @property
    def json_compatible_values(self) -> pd.Series:
        """
        Array of str or int or float values for the X axis of the chart.

        In particular: datetime64 values will be converted to str.
        """
        if self.column.type == "datetime":
            try:
                utc_series = self.series.dt.tz_convert(None).to_series()
            except TypeError:
                utc_series = self.series

            str_series = utc_series.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            str_series = str_series.mask(self.series.isna())  # 'NaT' => np.nan

            return str_series.values
        else:
            return self.series


@dataclass
class YSeries:
    series: pd.Series
    color: str
    tick_format: str
    """Python string format specifier, like '{:,}'."""

    @property
    def name(self):
        return self.series.name

    @property
    def d3_tick_format(self):
        return python_format_to_d3_tick_format(self.tick_format)


@dataclass
class Chart:
    """Fully-sane parameters. Columns are series."""

    title: str
    x_axis_label: str
    x_axis_tick_format: str
    y_axis_label: str
    x_series: XSeries
    y_columns: List[YSeries]
    y_axis_tick_format: str

    def to_vega_data_values(self) -> List[Dict[str, Any]]:
        """
        Build a dict for Vega's .data.values Array.

        Return value is a list of dict records. Each has
        {'x': 'X Name', 'line': 'Line Name', 'y': 1.0}
        """
        # We use column names 'x' and f'y{colname}' to prevent conflicts (e.g.,
        # colname='x'). After melt(), we'll drop the 'y' prefix.
        data = {"x": self.x_series.json_compatible_values}
        for y_column in self.y_columns:
            data["y" + y_column.name] = y_column.series
        dataframe = pd.DataFrame(data)
        vertical = dataframe.melt("x", var_name="line", value_name="y")
        vertical.dropna(inplace=True)
        vertical["line"] = vertical["line"].str[1:]  # drop 'y' prefix
        return vertical.to_dict(orient="records")

    def to_vega(self) -> Dict[str, Any]:
        """
        Build a Vega bar chart or grouped bar chart.
        """
        ret = {
            "$schema": "https://vega.github.io/schema/vega-lite/v3.json",
            "title": self.title,
            "config": {
                "title": {
                    "offset": 15,
                    "color": "#383838",
                    "font": "Nunito Sans, Helvetica, sans-serif",
                    "fontSize": 20,
                    "fontWeight": "normal",
                },
                "axis": {
                    "tickSize": 3,
                    "titlePadding": 20,
                    "titleFontSize": 15,
                    "titleFontWeight": 100,
                    "titleColor": "#686768",
                    "titleFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFontWeight": 400,
                    "labelColor": "#383838",
                    "labelFontSize": 12,
                    "labelPadding": 10,
                    "gridOpacity": 0.5,
                },
            },
            "data": {"values": self.to_vega_data_values()},
            "mark": {"type": "line", "point": {"shape": "circle"}},
            "encoding": {
                "x": {
                    "field": "x",
                    "type": self.x_series.vega_data_type,
                    "axis": {
                        "title": self.x_axis_label,
                        "format": self.x_axis_tick_format,
                        "tickMinStep": (
                            1
                            if (
                                self.x_axis_tick_format
                                and self.x_axis_tick_format[-1] == "d"
                            )
                            else None
                        ),
                    },
                },
                "y": {
                    "field": "y",
                    "type": "quantitative",
                    "axis": {
                        "title": self.y_axis_label,
                        "format": self.y_axis_tick_format,
                        "tickMinStep": (
                            1 if self.y_axis_tick_format[-1] == "d" else None
                        ),
                    },
                },
                "color": {
                    "field": "line",
                    "type": "nominal",
                    "scale": {
                        "domain": [y.name for y in self.y_columns],
                        "range": [y.color for y in self.y_columns],
                    },
                },
            },
        }

        if self.x_series.vega_data_type == "ordinal":
            ret["encoding"]["x"]["axis"].update(
                {"labelAngle": 0, "labelOverlap": False}
            )
            ret["encoding"]["x"]["sort"] = None
            ret["encoding"]["order"] = {"type": None}

        if len(self.y_columns) == 1:
            ret["encoding"]["color"]["legend"] = None
        else:
            ret["encoding"]["color"]["legend"] = {"title": None}
            ret["config"]["legend"] = {
                "symbolType": "circle",
                "titlePadding": 20,
                "padding": 15,
                "offset": 0,
                "labelFontSize": 12,
                "rowPadding": 10,
                "labelFont": "Nunito Sans, Helvetica, sans-serif",
                "labelColor": "#383838",
                "labelFontWeight": "normal",
            }

        return ret


@dataclass
class YColumn:
    column: str
    color: str


@dataclass
class Form:
    """
    Parameter dict specified by the user: valid types, unchecked values.
    """

    title: str
    x_axis_label: str
    y_axis_label: str
    x_column: str
    y_columns: List[YColumn]

    @classmethod
    def from_params(cls, *, y_columns: List[Dict[str, str]], **kwargs):
        return cls(**kwargs, y_columns=[YColumn(**d) for d in y_columns])

    def _make_x_series(
        self, table: pd.DataFrame, input_columns: Dict[str, Any]
    ) -> XSeries:
        """
        Create an XSeries ready for charting, or raise ValueError.
        """
        if not self.x_column:
            raise GentleValueError("Please choose an X-axis column")

        series = table[self.x_column]
        column = input_columns[self.x_column]
        nulls = series.isna()
        safe_x_values = series[~nulls]  # so we can min(), len(), etc
        safe_x_values.reset_index(drop=True, inplace=True)

        if column.type == "text" and len(safe_x_values) > MaxNAxisLabels:
            raise ValueError(
                f'Column "{self.x_column}" has {len(safe_x_values)} '
                "text values. We cannot fit them all on the X axis. "
                "Please change the input table to have 10 or fewer rows, or "
                f'convert "{self.x_column}" to number or date.'
            )

        if not len(safe_x_values):
            raise ValueError(
                f'Column "{self.x_column}" has no values. '
                "Please select a column with data."
            )

        if not len(safe_x_values[safe_x_values != safe_x_values[0]]):
            raise ValueError(
                f'Column "{self.x_column}" has only 1 value. '
                "Please select a column with 2 or more values."
            )

        return XSeries(series, column)

    def make_chart(self, table: pd.DataFrame, input_columns: Dict[str, Any]) -> Chart:
        """
        Create a Chart ready for charting, or raise ValueError.

        Features:
        * Error if X column is missing
        * Error if X column does not have two values
        * Error if X column is all-NaN
        * Error if too many X values in text mode (since we can't chart them)
        * X column can be number or date
        * Missing X dates lead to missing records
        * Missing X floats lead to missing records
        * Missing Y values are omitted
        * Error if no Y columns chosen
        * Error if a Y column is the X column
        * Error if a Y column has fewer than 1 non-missing value
        * Default title, X and Y axis labels
        """
        x_series = self._make_x_series(table, input_columns)
        if not self.y_columns:
            raise GentleValueError("Please choose a Y-axis column")

        y_columns = []
        for ycolumn in self.y_columns:
            if ycolumn.column == self.x_column:
                raise ValueError(
                    f'Cannot plot Y-axis column "{ycolumn.column}" '
                    "because it is the X-axis column"
                )

            series = table[ycolumn.column]

            if not is_numeric_dtype(series.dtype):
                raise ValueError(
                    f'Cannot plot Y-axis column "{ycolumn.column}" '
                    "because it is not numeric. "
                    "Convert it to a number before plotting it."
                )

            # Find how many Y values can actually be plotted on the X axis. If
            # there aren't going to be any Y values on the chart, raise an
            # error.
            matches = pd.DataFrame({"X": x_series.series, "Y": series}).dropna()
            if not matches["X"].count():
                raise ValueError(
                    f'Cannot plot Y-axis column "{ycolumn.column}" '
                    "because it has no values"
                )

            y_columns.append(
                YSeries(series, ycolumn.color, input_columns[ycolumn.column].format)
            )

        title = self.title or "Line Chart"
        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name

        return Chart(
            title=title,
            x_axis_label=x_axis_label,
            x_axis_tick_format=x_series.d3_tick_format,
            y_axis_label=y_axis_label,
            x_series=x_series,
            y_columns=y_columns,
            y_axis_tick_format=y_columns[0].d3_tick_format,
        )


def render(table, params, *, input_columns):
    form = Form.from_params(**params)
    try:
        chart = form.make_chart(table, input_columns)
    except GentleValueError as err:
        return (table, "", {"error": str(err)})
    except ValueError as err:
        return (table, str(err), {"error": str(err)})

    json_dict = chart.to_vega()
    return (table, "", json_dict)
