from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, List
import pandas
from pandas.api.types import is_numeric_dtype


MaxNBars = 500


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

    def to_vega_data_values(self) -> List[Dict[str, Any]]:
        """
        Build a dict for Vega's .data.values Array.

        Return value is a list of dict records. Each has
        {x_series.name: 'X Name', 'bar': 'Bar Name', 'y': 1.0}
        """
        x_series = self.x_series.series
        data = {
            # Only column name guaranteed to be unique: x_series.name
            self.x_series.name: list(zip(x_series.index, x_series.values)),
        }
        for y_column in self.y_columns:
            data[y_column.name] = y_column.series
        dataframe = pandas.DataFrame(data)
        melted = dataframe.melt(self.x_series.name, var_name='bar',
                                value_name='y')
        tuples = melted[self.x_series.name]
        del melted[self.x_series.name]
        melted['group'] = tuples.map(lambda x: x[0])
        melted['name'] = tuples.map(lambda x: x[1])

        return melted.to_dict(orient='records')

    def to_vega(self) -> Dict[str, Any]:
        """
        Build a Vega bar chart or grouped bar chart.
        """
        ret = {
            "$schema": "https://vega.github.io/schema/vega/v4.json",
            "background": "white",
            "title": {
                "text": self.title,
                "offset": 15,
                "color": '#383838',
                "font": "Nunito Sans, Helvetica, sans-serif",
                "fontSize": 20,
                "fontWeight": "normal"
            },

            "data": [
                {
                    "name": "table",
                    "values": self.to_vega_data_values(),
                }
            ],

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
                    }
                },
                {
                    "title": self.y_axis_label,
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
                        "facet": {
                            "data": "table",
                            "name": "facet",
                            "groupby": "group",
                        }
                    },

                    "encode": {
                        "enter": {
                            "x": {"scale": "xscale", "field": "group"},
                        }
                    },

                    "signals": [
                        {"name": "width", "update": "bandwidth('xscale')"}
                    ],

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
                                    "fill": {"scale": "color",
                                             "field": "bar"},
                                }
                            }
                        }
                    ]
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
                },
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

    def validate_with_table(self, table: pandas.DataFrame) -> SeriesParams:
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
                f'Column chart can visualize '
                f'a maximum of {MaxNBars} bars'
            )

        if not self.x_column:
            raise GentleValueError('Please choose an X-axis column')
        if not self.y_columns:
            raise GentleValueError('Please choose a Y-axis column')

        x_series = XSeries(table[self.x_column].astype(str))

        y_columns = []
        for y_column in self.y_columns:
            if y_column.column == self.x_column:
                raise ValueError(
                    f'You cannot plot Y-axis column {y_column.column} '
                    'because it is the X-axis column'
                )

            series = table[y_column.column]

            if not is_numeric_dtype(series.dtype):
                raise ValueError(
                    f'Cannot plot Y-axis column "{y_column.column}" '
                    'because it is not numeric. '
                    'Convert it to a number before plotting it.'
                )

            y_columns.append(YSeries(series, y_column.color))

        if not len(table):
            raise GentleValueError('no records to plot')

        title = self.title or 'Column Chart'
        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name

        return SeriesParams(title=title, x_axis_label=x_axis_label,
                            y_axis_label=y_axis_label, x_series=x_series,
                            y_columns=y_columns)


def _migrate_params_v0_to_v1(params):
    """
    v0: params['y_columns'] is JSON-encoded.

    v1: params['y_columns'] is List[Dict[{ name, color }, str]].
    """
    json_y_columns = params['y_columns']
    if not json_y_columns:
        # empty str => no columns
        y_columns = []
    else:
        y_columns = json.loads(json_y_columns)
    return {
        **params,
        'y_columns': y_columns
    }


def migrate_params(params):
    if isinstance(params['y_columns'], str):
        params = _migrate_params_v0_to_v1(params)

    return params


def render(table, params):
    form = Form.from_params(**params)
    try:
        valid_params = form.validate_with_table(table)
    except GentleValueError as err:
        return (table, '', {'error': str(err)})
    except ValueError as err:
        return (table, str(err), {'error': str(err)})

    json_dict = valid_params.to_vega()
    return (table, '', json_dict)
