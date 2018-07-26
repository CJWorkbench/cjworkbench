import json
from numpy import datetime64, float64, ndarray
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
    def __init__(self, series: ndarray, name: str):
        self.series = series
        self.name = name

    @property
    def data_type(self):
        return self.series.dtype.type


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
        data = {}
        if self.x_series.data_type == datetime64:
            strs = self.x_series.series.astype(str)
            strs = [s + 'Z' for s in strs]
            data[self.x_series.name] = strs
        else:
            data[self.x_series.name] = self.x_series.series
        for y_column in self.y_columns:
            data[y_column.name] = y_column.series
        dataframe = pandas.DataFrame(data)
        vertical = dataframe.melt(self.x_series.name, var_name='line',
                                  value_name='y')
        vertical.dropna(inplace=True)
        return vertical.to_dict(orient='records')

    def to_vega(self) -> Dict[str, Any]:
        """
        Build a Vega bar chart or grouped bar chart.
        """
        if self.x_series.data_type == datetime64:
            x_data_type = 'temporal'
        else:
            x_data_type = 'quantitative'

        ret = {
            "$schema": "https://vega.github.io/schema/vega-lite/v2.json",
            "title": self.title,

            "data": {
                "values": self.to_vega_data_values(),
            },

            "mark": {
                "type": "line",
                "point": {
                    "shape": "circle",
                }
            },

            "encoding": {
                "x": {
                    "field": self.x_series.name,
                    "type": x_data_type,
                    "axis": {"title": self.x_axis_label},
                },

                "y": {
                    "field": "y",
                    "type": "quantitative",
                    "axis": {"title": self.y_axis_label},
                },

                "color": {
                    "field": "line",
                    "type": "nominal",
                    "scale": {
                        "range": [y.color for y in self.y_columns],
                    }
                },
            }
        }

        if len(self.y_columns) == 1:
            ret['encoding']['color']['legend'] = None
        else:
            ret['encoding']['color']['legend'] = {
                'title': 'Legend',
                'shape': 'circle',
            }
            ret['config'] = {
                'legend': {
                    'symbolType': 'circle',
                }
            }

        return ret


class YColumn:
    def __init__(self, column: str, color: str):
        self.column = column
        self.color = color


def _coerce_x_series(series: pandas.Series, data_type: type) -> pandas.Series:
    """
    Convert `series` to `data_type`, replacing erroneous values.
    """
    if data_type == float64:
        x_floats = pandas.to_numeric(series, errors='coerce')
        x_floats.fillna(0.0, inplace=True)
        return x_floats
    else:
        # TODO:
        # * test "UTC" does what we expect
        # * test errors='coerce'
        # * test infer_datetime_format
        x_dates = pandas.to_datetime(series, utc=True, errors='coerce',
                                     infer_datetime_format=True)
        x_dates.fillna(datetime64(0, 's'), inplace=True)
        # pandas' dtype is not datetime64; np's is
        x_dates = x_dates.values.astype(datetime64)
        return x_dates


class UserParams:
    """
    Parameter dict specified by the user: valid types, unchecked values.
    """
    def __init__(self, *, title: str, x_axis_label: str, y_axis_label: str,
                 x_column: str, x_type: type, y_columns: List[YColumn]):
        self.title = title
        self.x_axis_label = x_axis_label
        self.y_axis_label = y_axis_label
        self.x_column = x_column
        self.x_type = x_type
        self.y_columns = y_columns

    @staticmethod
    def from_params(params: Dict[str, Any]) -> 'UserParams':
        title = str(params.get('title', ''))
        x_axis_label = str(params.get('x_axis_label', ''))
        y_axis_label = str(params.get('y_axis_label', ''))
        x_column = str(params.get('x_column', ''))
        if str(params.get('x_data_type')) == '1':
            x_type = datetime64
        else:
            x_type = float64
        y_columns = UserParams.parse_y_columns(
            params.get('y_columns', 'null')
        )
        return UserParams(title=title, x_axis_label=x_axis_label,
                          y_axis_label=y_axis_label, x_column=x_column,
                          x_type=x_type, y_columns=y_columns)

    def validate_with_table(self, table: pandas.DataFrame) -> SeriesParams:
        """
        Create a SeriesParams ready for charting, or raises ValueError.

        Features ([tested?]):
        [ ] Error if X column is missing
        [ ] Error if X column does not have two values
        [ ] X column can be number or date
        [ ] Missing dates are coerced to 1970-01-01
        [ ] Missing Y values are omitted
        [ ] Error if no Y columns chosen
        [ ] Error if no rows
        [ ] Error if too many bars
        [ ] Error if a Y column is missing
        [ ] Error if a Y column is the X column
        [ ] Error if a Y column has fewer than 1 non-missing value
        [ ] Default title, X and Y axis labels
        """
        if len(table.index) >= MaxNBars:
            raise ValueError(
                f'Refusing to build column chart with '
                'more than {MaxNBars} bars'
            )

        if self.x_column not in table.columns:
            raise GentleValueError('Please choose an X-axis column')
        if not self.y_columns:
            raise GentleValueError('Please choose a Y-axis column')

        x_values = _coerce_x_series(table[self.x_column], self.x_type)
        if x_values.min() == x_values.max():
            raise ValueError(
                f'Cannot plot X-axis column {self.x_column} '
                f'because it only has one {self.x_type.__name__} value'
            )
        x_series = XSeries(x_values, self.x_column)

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

            if not floats.count():
                raise ValueError(
                    f'You cannot plot Y-axis column {ycolumn.column} '
                    'because it nas no numeric data'
                )

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
