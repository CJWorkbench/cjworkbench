from __future__ import annotations

from dataclasses import dataclass
import json
from string import Formatter
from typing import Any, Dict, List
import numpy as np
import pandas
from pandas.api.types import is_numeric_dtype


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

    On first load, we don't want to display an error, even though the user
    hasn't selected what to chart. So we'll display the error in the iframe:
    we'll be gentle with the user.
    """


@dataclass(frozen=True)
class XSeries:
    series: pandas.Series

    @property
    def name(self):
        return self.series.name


@dataclass(frozen=True)
class YSeries:
    series: pandas.Series
    color: str

    @property
    def name(self):
        return self.series.name


@dataclass(frozen=True)
class SeriesParams:
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
        Build a dict for Vega's .data.values Array.

        Return value is a list of dict records. Each has
        {'bar': 'YCOLNAME', 'group': 2, 'y': 1.0}.

        The 'group' is an index into x_series (which we ignore here). Each
        "group" is a value in the X series, which we'll render as a set of
        bars.
        """

        # given input like:
        #    X  B  C    D
        # 0  x  1  2  NaN
        # 1  x  2  3  6.0
        # 2  y  3  4  7.0
        #
        # Produce `dataframe` like:
        #    B  C    D
        # 0  1  2  NaN
        # 1  2  3  6.0
        # 2  3  4  7.0
        #
        # (The "index" here is a "group id" -- an index into
        # self.x_series.series. We call that "group".)
        dataframe = pandas.DataFrame({yc.name: yc.series for yc in self.y_columns})

        # stacked: a series indexed by group, like:
        # group  bar
        # 0      B      1.0
        #        C      2.0
        #        D      nan
        # 1      B      2.0
        #        C      3.0
        #        D      6.0
        # 2      B      3.0
        #        C      4.0
        #        D      7.0
        stacked = dataframe.stack(dropna=False)
        stacked.name = "y"
        stacked.index.names = ["group", "bar"]

        # Now convert back to a dataframe. This is the data we'll pass to Vega.
        #
        # We need to output null (None) here instead of leaving records empty.
        # Otherwise, Vega will make some bars thicker than others.
        table = stacked.reset_index()

        # Change nulls from NaN to None (Object). NaN is invalid JSON.
        y = table["y"].astype(object)
        y[y.isnull()] = None
        table["y"] = y
        return table.to_dict("records")

    def to_vega(self) -> Dict[str, Any]:
        """
        Build a Vega bar chart or grouped bar chart.
        """
        ret = {
            "$schema": "https://vega.github.io/schema/vega/v5.json",
            "background": "white",
            "title": {
                "text": self.title,
                "offset": 15,
                "color": "#383838",
                "font": "Nunito Sans, Helvetica, sans-serif",
                "fontSize": 20,
                "fontWeight": "normal",
            },
            "data": [{"name": "table", "values": self.to_vega_data_values()}],
            "scales": [
                {
                    "name": "xscale",
                    "type": "band",
                    "domain": {"data": "table", "field": "group"},
                    "range": "width",
                    "padding": 0.15,
                },
                {
                    # This is a big hack. The idea is: the x-axis "labels.text"
                    # will be a function that converts a group's _value_ (that
                    # is, `table.group`) to its _name_ (table.name).
                    #
                    # Vega axes are a bit unintuitive here: our main x-axis is
                    # of _groups_, which have both name and position. The
                    # position needs "band" and the name needs "ordinal". Our
                    # only hope is to create two axes.
                    "name": "xname",
                    "type": "ordinal",
                    "domain": {"data": "table", "field": "group"},
                    "range": self.x_series.series.values.tolist(),
                },
                {
                    "name": "yscale",
                    "type": "linear",
                    "domain": {"data": "table", "field": "y"},
                    "range": "height",
                    "zero": True,
                    "nice": True,
                },
                {
                    "name": "color",
                    "type": "ordinal",
                    "domain": {"data": "table", "field": "bar"},
                    "range": [ys.color for ys in self.y_columns],
                },
            ],
            "axes": [
                {
                    "title": self.x_axis_label,
                    "orient": "bottom",
                    "scale": "xscale",
                    "tickSize": 0,
                    "titlePadding": 15,
                    "titleColor": "#686768",
                    "titleFontSize": 15,
                    "titleFontWeight": 100,
                    "titleFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFontWeight": "normal",
                    "labelPadding": 10,
                    "labelFontSize": 12,
                    "labelColor": "#383838",
                    "encode": {
                        "labels": {
                            "update": {
                                "text": {
                                    # [adamhooper, 2018-09-21] I never found
                                    # docs for this. What a crazy Chrome
                                    # Inspector session this took....
                                    "signal": "scale('xname', datum.value)"
                                }
                            }
                        }
                    },
                },
                {
                    "title": self.y_axis_label,
                    "format": self.y_label_format,
                    "tickMinStep": (1 if self.y_label_format.endswith("d") else None),
                    "orient": "left",
                    "scale": "yscale",
                    "tickSize": 3,
                    "labelOverlap": True,
                    "titleFontSize": 14,
                    "titleColor": "#686768",
                    "titleFontWeight": 100,
                    "titleFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelColor": "#383838",
                    "labelFontWeight": "normal",
                    "titlePadding": 20,
                    "labelPadding": 10,
                    "labelFontSize": 11,
                },
            ],
            "marks": [
                {
                    "type": "group",
                    "from": {
                        "facet": {"data": "table", "name": "facet", "groupby": "group"}
                    },
                    "encode": {"enter": {"x": {"scale": "xscale", "field": "group"}}},
                    "signals": [{"name": "width", "update": "bandwidth('xscale')"}],
                    "scales": [
                        {
                            "name": "pos",
                            "type": "band",
                            "range": "width",
                            "domain": {"data": "facet", "field": "bar"},
                        }
                    ],
                    "marks": [
                        {
                            "name": "bars",
                            "from": {"data": "facet"},
                            "type": "rect",
                            "encode": {
                                "enter": {
                                    "x": {"scale": "pos", "field": "bar"},
                                    "width": {"scale": "pos", "band": 1},
                                    "y": {"scale": "yscale", "field": "y"},
                                    "y2": {"scale": "yscale", "value": 0},
                                    "fill": {"scale": "color", "field": "bar"},
                                }
                            },
                        }
                    ],
                }
            ],
        }

        if len(self.y_columns) > 1:
            ret["legends"] = [
                {
                    "fill": "color",
                    "symbolType": "circle",
                    "padding": 15,
                    "offset": 0,
                    "labelFontSize": 12,
                    "rowPadding": 10,
                    "labelFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelColor": "#383838",
                    "labelFontWeight": "normal",
                }
            ]

        return ret


@dataclass(frozen=True)
class YColumn:
    column: str
    color: str


@dataclass(frozen=True)
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
    def from_params(cls, *, y_columns: List[Dict[str, str]], **kwargs) -> Form:
        return Form(**kwargs, y_columns=[YColumn(**y) for y in y_columns])

    def validate_with_table(
        self, table: pandas.DataFrame, input_columns: Dict[str, Any]
    ) -> SeriesParams:
        """
        Create a SeriesParams ready for charting, or raises ValueError.

        Features ([tested?]):
        [ ] Error if X column is missing
        [ ] Error if no Y columns chosen
        [ ] Error if no rows
        [ ] Error if too many bars
        [ ] Error if a Y column is missing
        [ ] Error if a Y column is the X column
        [ ] Error if a Y column is not numeric
        [ ] Default title, X and Y axis labels
        [ ] DOES NOT WORK - nix NA X values
        """
        if len(table.index) >= MaxNBars:
            raise ValueError(
                f"Column chart can visualize " f"a maximum of {MaxNBars} bars"
            )

        if not self.x_column:
            raise GentleValueError("Please choose an X-axis column")
        if not self.y_columns:
            raise GentleValueError("Please choose a Y-axis column")

        x_series = XSeries(table[self.x_column].astype(str))

        y_columns = []
        for y_column in self.y_columns:
            if y_column.column == self.x_column:
                raise ValueError(
                    f"You cannot plot Y-axis column {y_column.column} "
                    "because it is the X-axis column"
                )

            series = table[y_column.column]
            y_columns.append(YSeries(series, y_column.color))

        if not len(table):
            raise GentleValueError("no records to plot")

        title = self.title or "Column Chart"
        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name
        y_label_format = python_format_to_d3_tick_format(
            input_columns[y_columns[0].name].format
        )

        return SeriesParams(
            title=title,
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
        return (table, "", {"error": str(err)})
    except ValueError as err:
        return (table, str(err), {"error": str(err)})

    json_dict = valid_params.to_vega()
    return (table, "", json_dict)
