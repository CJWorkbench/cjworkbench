import json
from typing import Any, Dict, List
import pandas


MaxNBars = 500


class GentleValueError(ValueError):
    """
    A ValueError that should not display in red to the user.

    On first load, we don't want to display an error, even though the user
    hasn't selected what to chart. So we'll display the error in the iframe:
    we'll be gentle with the user.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class XSeries:
    def __init__(self, series: pandas.Series, name: str):
        self.series = series
        self.name = name


class YSeries:
    def __init__(self, series: pandas.Series, name: str, color: str):
        self.series = series
        self.name = name
        self.color = color


class SeriesParams:
    """
    Fully-sane parameters. Columns are series.
    """
    def __init__(self, *, title: str, x_axis_label: str, y_axis_label: str,
                 x_series: XSeries, y_columns: List[YSeries]):
        self.title = title
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.x_series = x_series
        self.y_columns = y_columns

    def to_vega_data_values(self) -> List[Dict[str, Any]]:
        """
        Build a dict for Vega's .data.values Array.

        Return value is a list of dict records. Each has
        {x_series.name: 'X Name', 'bar': 'Bar Name', 'y': 1.0}
        """
        data = {
            self.x_series.name: self.x_series.series,
        }
        for y_column in self.y_columns:
            data[y_column.name] = y_column.series
        dataframe = pandas.DataFrame(data)
        return dataframe.melt(self.x_series.name, var_name='bar',
                              value_name='y').to_dict(orient='records')

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
                    "domain": {"data": "table", "field": self.x_series.name},
                    "range": "width",
                    "padding": 0.15,
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
                }
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
                    "labelFontWeight":400,
                    "labelPadding": 10,
                    "labelFontSize": 12,
                    "labelColor":"#383838",

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
                    "labelFontWeight":400,
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
                            "groupby": self.x_series.name,
                        }
                    },

                    "encode": {
                        "enter": {
                            "x": {"scale": "xscale",
                                  "field": self.x_series.name},
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
                    "labelFontWeight":400,
                },
            ]

        return ret


class YColumn:
    def __init__(self, column: str, color: str):
        self.column = column
        self.color = color


class UserParams:
    """
    Parameter dict specified by the user: valid types, unchecked values.
    """
    def __init__(self, *, title: str, x_axis_label: str, y_axis_label: str,
                 x_column: str, y_columns: List[YColumn]):
        self.title = title
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.x_column = x_column
        self.y_columns = y_columns

    @staticmethod
    def from_params(params: Dict[str, Any]) -> 'UserParams':
        title = str(params.get('title', ''))
        x_axis_label = str(params.get('x_axis_label', ''))
        y_axis_label = str(params.get('y_axis_label', ''))
        x_column = str(params.get('x_column', ''))
        y_columns = UserParams.parse_y_columns(
            params.get('y_columns', 'null')
        )
        return UserParams(title=title, x_axis_label=x_axis_label,
                          y_axis_label=y_axis_label, x_column=x_column,
                          y_columns=y_columns)

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
        [ ] Default title, X and Y axis labels
        """
        if len(table.index) >= MaxNBars:
            raise ValueError(
                f'Column chart can visualize '
                f'a maximum of {MaxNBars} bars'
            )

        if self.x_column not in table.columns:
            raise GentleValueError('Please choose an X-axis column')
        if not self.y_columns:
            raise GentleValueError('Please choose a Y-axis column')

        x_series = XSeries(table[self.x_column].astype(str), self.x_column)

        y_columns = []
        for ycolumn in self.y_columns:
            if ycolumn.column not in table.columns:
                raise ValueError(
                    f'Cannot plot Y-axis column {ycolumn.column} '
                    'because it does not exist'
                )
            elif ycolumn.column == self.x_column:
                raise ValueError(
                    f'You cannot plot Y-axis column {ycolumn.column} '
                    'because it is the X-axis column'
                )

            series = table[ycolumn.column]
            floats = pandas.to_numeric(series, errors='coerce')
            floats.fillna(0.0, inplace=True)
            y_columns.append(YSeries(floats, ycolumn.column, ycolumn.color))

        if not len(table):
            raise GentleValueError('no records to plot')

        title = self.title or 'Column Chart'
        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name

        return SeriesParams(title=title, x_axis_label=x_axis_label,
                            y_axis_label=y_axis_label, x_series=x_series,
                            y_columns=y_columns)

    @staticmethod
    def parse_y_columns(s):
        try:
            arr = json.loads(s)
            return [YColumn(str(o.get('column', '')),
                            str(o.get('color', '#000000')))
                    for o in arr]
        except json.decoder.JSONDecodeError:
            # Not valid JSON
            return []
        except TypeError:
            # arr is not iterable
            return []
        except AttributeError:
            # an element of arr is not a dict
            return []


def render(table, params):
    user_params = UserParams.from_params(params)
    try:
        valid_params = user_params.validate_with_table(table)
    except GentleValueError as err:
        return (table, '', {'error': str(err)})
    except ValueError as err:
        return (table, str(err), {'error': str(err)})

    json_dict = valid_params.to_vega()
    return (table, '', json_dict)
