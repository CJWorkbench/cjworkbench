import enum
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from cjwmodule.i18n import trans

# ---- CountByDate ----
# group column by unique value, discard all other columns


class UserVisibleError(Exception):
    """An exception that has a `i18n.I18nMessage` as its first argument. Use `err.i18n_message` to see it."""

    @property
    def i18n_message(self):
        return self.args[0]


class Period(enum.Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    SECOND_OF_DAY = "second_of_day"
    MINUTE_OF_DAY = "minute_of_day"
    HOUR_OF_DAY = "hour_of_day"

    @property
    def is_time_of_day(self):
        return (
            self == Period.SECOND_OF_DAY
            or self == Period.MINUTE_OF_DAY
            or self == Period.HOUR_OF_DAY
        )

    @property
    def pandas_freq(self):
        return {
            Period.SECOND: "S",
            Period.MINUTE: "T",
            Period.HOUR: "H",
            Period.DAY: "D",
            Period.MONTH: "M",
            Period.QUARTER: "Q",
            Period.YEAR: "Y",
            Period.SECOND_OF_DAY: "S",
            Period.MINUTE_OF_DAY: "T",
            Period.HOUR_OF_DAY: "H",
        }[self]

    @property
    def strftime_format(self):
        """If set, output must be cast to str using this format."""
        return {
            Period.QUARTER: "%Y Q%q",
            Period.SECOND_OF_DAY: "%H:%M:%S",
            Period.MINUTE_OF_DAY: "%H:%M",
            Period.HOUR_OF_DAY: "%H:00",
        }.get(
            self
        )  # usually `None`


class Operation(enum.Enum):
    # values are Python .agg() function names
    SIZE = "size"
    MEAN = "mean"
    SUM = "sum"
    MIN = "min"
    MAX = "max"

    @property
    def only_numeric(self):
        return self == Operation.MEAN or self == Operation.SUM

    @property
    def agg_function_name(self):
        """Pandas agg() function name."""
        return self.value

    @property
    def zero_value(self):
        """Value to impute when there are no inputs to agg_function_name."""
        if self in (Operation.SIZE, Operation.SUM):
            return 0
        else:
            return np.nan


class ValidatedForm:
    """User input, (almost) free of potential errors."""

    def __init__(
        self,
        date_series: pd.Series,
        period: Period,
        operation: Operation,
        value_series: Optional[pd.Series],
        output_date_column: str,
        output_value_column: str,
        include_missing_dates: bool,
        settings: object,
    ):
        self.date_series = date_series
        self.period = period
        self.operation = operation
        self.value_series = value_series
        self.output_date_column = output_date_column
        self.output_value_column = output_value_column
        self.include_missing_dates = include_missing_dates
        self.settings = settings

    def run(self):
        # input_dataframe: drop all rows for which either date or value (if
        # specified) is NA
        input_data = {"date": self.date_series}
        if self.value_series is None:
            input_data["value"] = np.full(len(self.date_series), 1, np.int64)
        else:
            input_data["value"] = self.value_series
        input_dataframe = pd.DataFrame(input_data)
        input_dataframe.dropna(inplace=True)

        # input_series: Series indexed by PeriodIndex
        period_index = pd.PeriodIndex(
            input_dataframe["date"].values, freq=self.period.pandas_freq
        )
        input_series = pd.Series(input_dataframe["value"].values, index=period_index)

        # output_series: Grouped
        grouped_series = input_series.groupby(input_series.index).agg(
            self.operation.agg_function_name
        )

        # Sort by date
        grouped_series.sort_index(inplace=True)

        # Impute missing values
        if self.include_missing_dates:
            start = period_index.min()
            if start is not pd.NaT:
                end = period_index.max()
                n_rows = (end - start).n + 1

                if n_rows > self.settings.MAX_ROWS_PER_TABLE:
                    raise UserVisibleError(
                        trans(
                            "error.tooManyRows",
                            "Including missing dates would create {n_rows} rows, "
                            "but the maximum allowed is {max_rows_per_table}",
                            {
                                "n_rows": n_rows,
                                "max_rows_per_table": self.settings.MAX_ROWS_PER_TABLE,
                            },
                        )
                    )
                new_index = pd.period_range(
                    start=start, end=end, freq=period_index.freq
                )
                grouped_series = grouped_series.reindex(
                    new_index, fill_value=self.operation.zero_value
                )

        # Prepare output dataframe
        output_periods = grouped_series.index
        output_values = grouped_series.values

        # strftime if needed
        if self.period.strftime_format:
            output_dates = output_periods.strftime(self.period.strftime_format)
        else:
            output_dates = output_periods.to_timestamp()

        return pd.DataFrame(
            {
                self.output_date_column: output_dates,
                self.output_value_column: output_values,
            }
        )


class Form:
    """Raw user input."""

    def __init__(
        self,
        date_column: str,
        period: Period,
        operation: Operation,
        value_column: str,
        include_missing_dates: bool,
        settings: object,
    ):
        self.date_column = date_column
        self.period = period
        self.operation = operation
        self.value_column = value_column
        self.include_missing_dates = include_missing_dates
        self.settings = settings

    @staticmethod
    def parse(d: Dict[str, Any], settings: object) -> Optional["Form"]:
        """
        Create a Form, raising IndexError/KeyError/ValueError on invalid input.

        The Form isn't validated against any data, so the only errors we raise
        here are errors in client code or in Workbench proper -- for instance,
        missing dict entries.
        """
        date_column = str(d["column"] or "")
        if not date_column:
            return None

        value_column = str(d["targetcolumn"] or "")
        period = Period(d["groupby"])
        operation = Operation(d["operation"])
        include_missing_dates = bool(d["include_missing_dates"])

        if operation != Operation.SIZE and not value_column:
            return None  # waiting for user to finish filling out the form....

        return Form(
            date_column,
            period,
            operation,
            value_column,
            include_missing_dates,
            settings=settings,
        )

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

        if self.period.is_time_of_day:
            # Convert all dates to 1970-01-01
            date_series = (
                date_series
                - date_series.dt.normalize()  # drop the actual date
                + np.datetime64("1970-01-01")  # and put 1970-01-01 instead
            )

        if self.operation != Operation.SIZE:
            output_value_column = self.value_column
            value_series = table[self.value_column]

            if self.operation.only_numeric and not is_numeric_dtype(value_series):
                if hasattr(value_series, "dt"):
                    raise DatetimeIsNotNumeric(self.value_column)
                else:
                    raise TextIsNotNumeric(self.value_column)
        else:
            output_value_column = "count"
            value_series = None

        return ValidatedForm(
            date_series,
            self.period,
            self.operation,
            value_series,
            self.date_column,
            output_value_column,
            self.include_missing_dates,
            settings=self.settings,
        )


def render(table, params, *, settings, **kwargs):
    if table is None or table.empty:
        return table

    try:
        form = Form.parse(params, settings)
    except (IndexError, KeyError, ValueError) as err:
        return str(err)
    if form is None:
        return table

    try:
        validated_form = form.validate(table)
    except ValueError as err:
        return str(err)

    try:
        return validated_form.run()
    except ValueError as err:
        return str(err)
    except UserVisibleError as err:
        return err.i18n_message


def _migrate_params_v0_to_v1(params):
    """
    v0: 'groupby' indexes into second|minute|hour|day|month|quarter|year
                               |second_of_day|minute_of_day|hour_of_day
    and 'operation' indexes into 'size|mean|sum|min|max'

    v1: the values are the values.
    """
    return {
        **params,
        "groupby": [
            "second",
            "minute",
            "hour",
            "day",
            "month",
            "quarter",
            "year",
            "second_of_day",
            "minute_of_day",
            "hour_of_day",
        ][params["groupby"]],
        "operation": ["size", "mean", "sum", "min", "max"][params["operation"]],
    }


def migrate_params(params):
    if isinstance(params["groupby"], int):
        params = _migrate_params_v0_to_v1(params)
    return params
