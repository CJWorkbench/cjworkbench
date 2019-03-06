from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
from pandas.api.types import is_numeric_dtype


class InputFormat(Enum):
    AUTO = 'auto'
    US = 'us'
    EU = 'eu'

    @property
    def kwargs(self):
        return {
            InputFormat.AUTO: {
                'infer_datetime_format': True,
                'format': None
            },
            InputFormat.US: {
                'infer_datetime_format': False,
                'format': '%m/%d/%Y'
            },
            InputFormat.EU: {
                'infer_datetime_format': False,
                'format': '%d/%m/%Y'
            }
        }[self]


@dataclass
class ErrorCount:
    """
    Tally of errors in all rows.

    This stores the first erroneous value and a count of all others. It's false
    if there aren't any errors.
    """

    a_column: Optional[str] = None
    a_row: Optional[int] = None
    a_value: Optional[str] = None
    total: int = 0
    n_columns: int = 0

    def __add__(self, rhs: 'ErrorCount') -> 'ErrorCount':
        """Add more errors to this ErrorCount."""
        return ErrorCount(self.a_column or rhs.a_column,
                          self.a_row or rhs.a_row,
                          self.a_value or rhs.a_value,
                          self.total + rhs.total,
                          self.n_columns + rhs.n_columns)

    def __str__(self):
        if self.total == 1:
            n_errors_str = 'is 1 error'
        else:
            n_errors_str = f'are {self.total} errors'

        if self.n_columns == 1:
            n_columns_str = '1 column'
        else:
            n_columns_str = f'{self.n_columns} columns'

        return (
            f"'{self.a_value}' in row {self.a_row + 1} of "
            f"'{self.a_column}' cannot be converted. Overall, there "
            f"{n_errors_str} in {n_columns_str}. Select 'non-dates "
            "to null' to set these values to null"
        )

    def __len__(self):
        """
        Count errors. 0 (which means __bool__ is false) if there are none.
        """
        return self.total

    @staticmethod
    def from_diff(in_series, out_series) -> 'ErrorCount':
        in_na = in_series.isna()
        out_na = out_series.isna()
        out_errors = out_na.index[out_na & ~in_na]

        if out_errors.empty:
            return ErrorCount()
        else:
            column = in_series.name
            row = out_errors[0]
            value = in_series[row]
            return ErrorCount(column, row, value, len(out_errors), 1)


def render(table, params):
    # No processing if no columns selected
    if not params['colnames']:
        return table

    columns = list(params['colnames'].split(','))
    input_format = InputFormat(params['input_format'])

    error_count = ErrorCount()

    for column in columns:
        in_series = table[column]

        kwargs = {**input_format.kwargs}

        if is_numeric_dtype(in_series):
            # For now, assume value is year and cast to string
            kwargs['format'] = '%Y'

        out_series = pd.to_datetime(in_series, errors='coerce', exact=False,
                                    cache=True, **kwargs)

        if not params['error_means_null']:
            error_count += ErrorCount.from_diff(in_series, out_series)

        table[column] = out_series

    if error_count:
        return str(error_count)

    return table


def _migrate_params_v0_to_v1(params):
    """
    v0: 'type_null' (bool), 'type_date' (input format AUTO|US|EU index)

    v1: 'error_means_null' (bool), 'input_format' (enum 'auto'|'us'|'eu')
    """
    return {
        'colnames': params['colnames'],
        'error_means_null': params['type_null'],
        'input_format': ['auto', 'us', 'eu'][params['type_date']]
    }


def migrate_params(params):
    if 'type_date' in params:
        params = _migrate_params_v0_to_v1(params)

    return params
