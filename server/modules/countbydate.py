import enum
from typing import Any, Dict, Optional
from django.conf import settings
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

# ---- CountByDate ----
# group column by unique value, discard all other columns


class InputTimeType(enum.Enum):
    DATE = 1
    DATETIME = 2
    TIME_OF_DAY = 3


class Period(enum.Enum):
    SECOND = 0
    MINUTE = 1
    HOUR = 2
    DAY = 3
    MONTH = 4
    QUARTER = 5
    YEAR = 6
    SECOND_OF_DAY = 7
    MINUTE_OF_DAY = 8
    HOUR_OF_DAY = 9

    @property
    def is_time_of_day(self):
        return (
            self == Period.SECOND_OF_DAY
            or self == Period.MINUTE_OF_DAY
            or self == Period.HOUR_OF_DAY
        )

    @property
    def pandas_freq(self):
        return 'STHDMQYSTH'[self.value]

    @property
    def strftime_format(self):
        """If set, output must be cast to str using this format."""
        return [
            None,
            None,
            None,
            None,
            None,
            '%Y Q%q',
            None,
            '%H:%M:%S',
            '%H:%M',
            '%H:00',
        ][self.value]


class Operation(enum.Enum):
    COUNT = 0
    AVERAGE = 1
    SUM = 2
    MIN = 3
    MAX = 4

    @property
    def only_numeric(self):
        return (
            self == Operation.AVERAGE
            or self == Operation.SUM
        )

    @property
    def agg_function_name(self):
        """Pandas agg() function name."""
        return [
            'size',
            'mean',
            'sum',
            'min',
            'max',
        ][self.value]

    @property
    def zero_value(self):
        """Value to impute when there are no inputs to agg_function_name."""
        return [
            0,
            np.NaN,
            0,
            np.NaN,
            np.NaN,
        ][self.value]


class ValidatedForm:
    """User input, (almost) free of potential errors."""
    def __init__(self, date_series: pd.Series, period: Period,
                 operation: Operation, value_series: Optional[pd.Series],
                 output_date_column: str, output_value_column: str,
                 include_missing_dates: bool):
        self.date_series = date_series
        self.period = period
        self.operation = operation
        self.value_series = value_series
        self.output_date_column = output_date_column
        self.output_value_column = output_value_column
        self.include_missing_dates = include_missing_dates

    def run(self):
        # input_dataframe: drop all rows for which either date or value (if
        # specified) is NA
        input_data = {'date': self.date_series}
        if self.value_series is None:
            input_data['value'] = 1
        else:
            input_data['value'] = self.value_series
        input_dataframe = pd.DataFrame(input_data)
        input_dataframe.dropna(inplace=True)

        # input_series: Series indexed by PeriodIndex
        period_index = pd.PeriodIndex(input_dataframe['date'].values,
                                      freq=self.period.pandas_freq)
        input_series = pd.Series(input_dataframe['value'].values,
                                 index=period_index)

        # output_series: Grouped
        grouped_series = input_series.groupby(input_series.index) \
            .agg(self.operation.agg_function_name)

        # Sort by date
        grouped_series.sort_index(inplace=True)

        # Impute missing values
        if self.include_missing_dates:
            start = period_index.min()
            if start is not pd.NaT:
                end = period_index.max()
                n_rows = (end - start).n + 1

                if n_rows > settings.MAX_ROWS_PER_TABLE:
                    raise ValueError(
                        f'Including missing dates would create {n_rows} rows, '
                        f'but the maximum allowed is '
                        f'{settings.MAX_ROWS_PER_TABLE}'
                    )
                new_index = pd.period_range(start=start, end=end,
                                            freq=period_index.freq)
                grouped_series = grouped_series.reindex(
                    new_index,
                    fill_value=self.operation.zero_value
                )

        # Prepare output dataframe
        output_periods = grouped_series.index
        output_values = grouped_series.values

        # strftime if needed
        if self.period.strftime_format:
            output_dates = output_periods.strftime(self.period.strftime_format)
        else:
            output_dates = output_periods.to_timestamp()

        return pd.DataFrame({
            self.output_date_column: output_dates,
            self.output_value_column: output_values,
        })


class QuickFixableError(ValueError):
    def __init__(self, message, quick_fixes=[]):
        super().__init__(message)
        self.quick_fixes = list(quick_fixes)


class NumericIsNotDatetime(ValueError):
    def __init__(self, column):
        super().__init__(f'Column "{column}" must be Date & Time')


class TextIsNotDatetime(QuickFixableError):
    def __init__(self, column):
        super().__init__(
            f'Column "{column}" must be Date & Time',
            [
                {
                    'text': 'Convert',
                    'action': 'prependModule',
                    'args': ['convert-date', {
                        'colnames': column,  # TODO make 'colnames' an Array
                    }]
                }
            ]
        )


class TextIsNotNumeric(QuickFixableError):
    def __init__(self, column):
        super().__init__(
            f'Column "{column}" must be numbers',
            [
                {
                    'text': 'Convert text to numbers',
                    'action': 'prependModule',
                    'args': ['extractnumbers', {
                        'colnames': column,  # TODO make 'colnames' Array
                        'extract': False,  # "anywhere in text"
                        'type_format': 0,  # U.S.-style "1,000.23"
                        'type_replace': 0,  # raise error on invalid
                    }]
                }
            ]
        )


class DatetimeIsNotNumeric(ValueError):
    def __init__(self, column):
        super().__init__(f'Column "{column}" must be numbers')


class Form:
    """Raw user input."""
    def __init__(self, date_column: str, period: Period, operation: Operation,
                 value_column: str, include_missing_dates: bool):
        self.date_column = date_column
        self.period = period
        self.operation = operation
        self.value_column = value_column
        self.include_missing_dates = include_missing_dates

    @staticmethod
    def parse(d: Dict[str, Any]) -> Optional['Form']:
        """
        Create a Form, raising IndexError/KeyError/ValueError on invalid input.

        The Form isn't validated against any data, so the only errors we raise
        here are errors in client code or in Workbench proper -- for instance,
        missing dict entries.
        """
        date_column = str(d['column'] or '')
        if not date_column:
            return None

        value_column = str(d['targetcolumn'] or '')
        period = Period(d['groupby'])
        operation = Operation(d['operation'])
        include_missing_dates = bool(d['include_missing_dates'])

        if operation != Operation.COUNT and not value_column:
            return None  # waiting for user to finish filling out the form....

        return Form(date_column, period, operation, value_column,
                    include_missing_dates)

    def validate(self, table):
        """
        Create a ValidatedForm or raise ValueError/PromptingError.

        Features ([ ] unit-tested):

        [ ] date column must exist
        [ ] if date column is numeric, error
        [ ] if date column is text, error+quickfix
        [ ] if period is time-of-day, dates are all 1970-01-01
        [ ] if operation isn't count, value column must exist
        [ ] if operation is sum/average, and value is datetime, error
        [ ] if operation is sum/average, and value is text, error+quickfix
        [ ] if operation is count, output column is 'count'; else it is value
        """
        date_series = table[self.date_column]

        if not hasattr(date_series, 'dt'):
            if is_numeric_dtype(date_series):
                raise NumericIsNotDatetime(self.date_column)
            else:
                raise TextIsNotDatetime(self.date_column)

        if self.period.is_time_of_day:
            # Convert all dates to 1970-01-01
            date_series = (
                date_series
                - date_series.dt.normalize()   # drop the actual date
                + np.datetime64('1970-01-01')  # and put 1970-01-01 instead
            )

        if self.operation != Operation.COUNT:
            output_value_column = self.value_column
            value_series = table[self.value_column]

            if (
                self.operation.only_numeric
                and not is_numeric_dtype(value_series)
            ):
                if hasattr(value_series, 'dt'):
                    raise DatetimeIsNotNumeric(self.value_column)
                else:
                    raise TextIsNotNumeric(self.value_column)
        else:
            output_value_column = 'count'
            value_series = None

        return ValidatedForm(date_series, self.period, self.operation,
                             value_series, self.date_column,
                             output_value_column, self.include_missing_dates)


def render(table, params, **kwargs):
    if table is None or table.empty:
        return table

    try:
        form = Form.parse(params)
    except (IndexError, KeyError, ValueError) as err:
        return str(err)
    if form is None:
        return table

    try:
        validated_form = form.validate(table)
    except QuickFixableError as err:
        return {
            'error': str(err),
            'quick_fixes': err.quick_fixes
        }
    except ValueError as err:
        return str(err)

    try:
        return validated_form.run()
    except ValueError as err:
        return str(err)
