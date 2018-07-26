from datetime import datetime
from enum import Enum
import re
from typing import Any, Optional, Tuple
from django.conf import settings
from dateutil.parser import parse
import numpy as np
import pandas as pd
from pandas.core.dtypes.common import is_dtype_equal
from .moduleimpl import ModuleImpl

# ---- CountByDate ----
# group column by unique value, discard all other columns

DEFAULT_DATETIME = datetime(1970, 1, 1, 0, 0, 0)
ALT_DEFAULT_DATETIME = datetime(1971, 2, 2, 1, 1, 1)


class InputTimeType(Enum):
    DATE = 1
    DATETIME = 2
    TIME_OF_DAY = 3


InvalidDate = re.compile('^\d+$')


def _parse_datetime_with_type(date_str: str) -> Tuple[datetime,
                                                      Optional[InputTimeType]]:
    """Return date with its type, or raise ValueError."""
    if not date_str:
        return (None, None)  # NaT

    if len(date_str) < 3 or InvalidDate.fullmatch(date_str):
        raise ValueError(f'"{date_str}" is not a date')

    ret = parse(date_str, default=DEFAULT_DATETIME)  # or raise ValueError

    input_time_type = InputTimeType.DATETIME

    if ret.hour == DEFAULT_DATETIME.hour \
       and ret.minute == DEFAULT_DATETIME.minute \
       and ret.second == DEFAULT_DATETIME.second:
        # suspicious: did parse() fill in the default hour/minute/second?
        # If so, perhaps this is just a plain date.
        alt = parse(date_str, default=ALT_DEFAULT_DATETIME)
        if alt.hour == ALT_DEFAULT_DATETIME.hour \
           and alt.minute == ALT_DEFAULT_DATETIME.minute \
           and alt.second == ALT_DEFAULT_DATETIME.second:
            # now we _know_ parse() filled in defaults. This date has no time.
            input_time_type = InputTimeType.DATE

    if ret.year == DEFAULT_DATETIME.year \
       and ret.month == DEFAULT_DATETIME.month \
       and ret.day == DEFAULT_DATETIME.day:
        # suspicious: did parse() fill in the default year/month/day?
        # If so, perhaps this is just a plain time.
        alt = parse(date_str, default=ALT_DEFAULT_DATETIME)
        if alt.year == ALT_DEFAULT_DATETIME.year \
           and alt.month == ALT_DEFAULT_DATETIME.month \
           and alt.day == ALT_DEFAULT_DATETIME.day:
            # now we _know_ parse() filled in defaults. This time has no date.
            input_time_type = InputTimeType.TIME_OF_DAY

    return (ret, input_time_type)


def cast_to_datetime_index(series: pd.Series
                           ) -> Tuple[pd.DatetimeIndex, InputTimeType]:
    """
    Parse an input series to `(DatetimeIndex, metadata)`.

    On invalid input, raise ValueError or TypeError.
    """
    str_series = series.astype(str)  # raise on invalid obj.__str__()
    # raise on non-date string
    date_and_type_series = str_series.apply(_parse_datetime_with_type)

    date_index = pd.DatetimeIndex(
        date_and_type_series.apply(lambda pair: pair[0]),
        name=series.name
    )

    # What do we have most? Date? Time? Datetime?
    type_series = date_and_type_series.apply(lambda pair: pair[1])
    input_type_counts = type_series.value_counts()
    if input_type_counts.max() / len(input_type_counts) > 0.8:
        # If we have predominantly one type, use that
        input_type = input_type_counts.idxmax()

        if input_type == InputTimeType.TIME_OF_DAY:
            # Make sure all datetimes have the same DATE (nix time-of-day)
            date_index = pd.DatetimeIndex(
                date_index.values
                - date_index.values.astype('datetime64[D]')  # timediff
                + np.datetime64('1970-01-01'),  # time after epoch
                name=series.name
            )
        elif input_type == InputTimeType.DATE:
            # Make sure all datetimes have the same TIME (nix date)
            date_index = date_index.normalize()
    else:
        # Be safe: use DateTime
        input_type = InputTimeType.DATETIME

    return (date_index, input_type)


def cast_to_numeric_series(series: pd.Series) -> pd.Series:
    """Return a (int|float)64 series or raise ValueError."""
    if series.dtype == np.float64 or series.dtype == np.int64:
        return series
    else:
        series = series.str.replace(',', '')  # raise ValueError on bad __str__
        series.astype(np.float64, inplace=True)  # raise ValueError on non-num
        return series


def get_period_time_formatter(freq: str,
                              is_time_only: bool) -> Optional[str]:
    """Build a template for `pandas.Period.strftime()`."""
    return {
        (False, 'S'): "%Y-%m-%dT%H:%M:%S",  # Seconds
        (False, 'T'): "%Y-%m-%dT%H:%M",  # Minutes
        (False, 'H'): "%Y-%m-%dT%H:00",  # Hours
        (False, 'D'): "%Y-%m-%d",  # Days
        (False, 'M'): "%Y-%m",  # Months
        (False, 'Q'): "%Y Q%q",  # Quarters -- pandas.Period-specific format
        (False, 'Y'): "%Y",  # Years
        (True, 'S'): "%H:%M:%S",  # Seconds
        (True, 'T'): "%H:%M",  # Minutes
        (True, 'H'): "%H:00",  # Hours
    }.get((is_time_only, freq), None)


def get_freq(groupby: int) -> Optional[str]:
    """Build a `freq` specifier for a `pandas.DatetimeIndex.to_period."""
    return {
        0: 'S',
        1: 'T',
        2: 'H',
        3: 'D',
        4: 'M',
        5: 'Q',
        6: 'Y',
    }.get(int(groupby), None)


def get_operation(index: int,
                  input_colname: Optional[str]) -> Tuple[str, Any,
                                                         Optional[str],
                                                         Optional[type]]:
    """
    Look up `(agg, zero_value, colname, out_type)` for an op by its index.

    `agg` is an argument to pandas.DataFrame.aggregate(). `zero_value` is the
    value we add when the user asks to include dates that were not in the data.

    Returning an `out_type` of `None` means, "use the same encoding as the
    input" (unless we add NaN, in which case output is float64).

    On invalid input, return (None, None, None, None).
    """
    return {
        0: ('size', 0, None, np.int64),
        1: ('mean', np.NaN, input_colname, np.float64),
        2: ('sum', 0, input_colname, None),
        3: ('min', np.NaN, input_colname, None),
        4: ('max', np.NaN, input_colname, None),
    }.get(int(index), (None, None, None, None))


class CountByDate(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        if table is None:
            return None

        col = wf_module.get_param_column('column')
        if not col:
            # Still waiting on user input
            # return (table, 'Please select a column containing dates')
            return table  # user has not input things yet
        if col not in table.columns:
            return f'There is no column named \'{col}\''

        target = wf_module.get_param_column('targetcolumn')

        freq = get_freq(wf_module.get_param_menu_idx('groupby'))
        if freq is None:
            return (table, 'Please select a valid time period')

        agg, zero_value, output_colname, output_type = get_operation(
            wf_module.get_param_menu_idx('operation'),
            target
        )
        if agg is None:  # should never happen
            return (table, 'Please select an operation')
        if output_colname == target:
            if not target:
                # Still waiting on user input
                return table
            elif target not in table.columns:
                return f'There is no column named \'{target}\''

        include_missing_dates = bool(
            wf_module.get_param_checkbox('include_missing_dates')
        )

        # convert the date column to actual datetimes
        try:
            dates, time_type = cast_to_datetime_index(table[col])
        except (ValueError, TypeError):
            return f'The column \'{col}\' does not appear to be dates or times'

        # Figure out our groupby options and groupby
        # behavior based on the input format.

        if time_type == InputTimeType.DATE and freq in ['S', 'T', 'H']:
            return (
                f'The column \'{col}\' only contains date values. '
                'Please group by Day, Month, Quarter or Year.'
            )
        if time_type == InputTimeType.TIME_OF_DAY and freq not in ['S', 'T', 'H']:
            return (
                f'The column \'{col}\' only contains time values. '
                'Please group by Second, Minute or Hour.'
            )

        periods = dates.to_period(freq)

        if output_colname is None:
            values = periods  # count the dates
        else:
            try:
                values = cast_to_numeric_series(table[target]).values
            except ValueError:
                return f'Can\'t convert {target} to numeric values'

        value_series = pd.Series(values, index=periods)
        value_series = value_series.dropna()
        grouped_values = value_series.groupby(value_series.index)
        # return_series has a PeriodIndex and numeric values
        return_series = grouped_values.agg(agg)
        return_series.name = output_colname or 'count'

        if include_missing_dates:
            end = periods.max()
            start = periods.min()
            n_rows = (end - start).n + 1
            if n_rows > settings.MAX_ROWS_PER_TABLE:
                return (
                    f'Including missing dates would create {n_rows} rows, '
                    f'but the maximum allowed is {settings.MAX_ROWS_PER_TABLE}'
                )

            index = pd.PeriodIndex(start=start, end=end,
                                   freq=periods.freq)
            return_series = return_series.reindex(index)
            if zero_value is not np.nan:
                return_series.fillna(zero_value, inplace=True)

        if output_type is None:
            output_type = values.dtype

        if is_dtype_equal(output_type, np.int64) \
           and return_series.isna().any():
            pass
        elif is_dtype_equal(output_type, np.float64):
            # we'd need a proof ... but basically: we're always float at this
            # point
            pass
        else:
            return_series = return_series.astype(output_type)

        return_series.sort_index(inplace=True)  # sort by date (index)

        time_format = get_period_time_formatter(
            freq,
            time_type == InputTimeType.TIME_OF_DAY
        )
        output = pd.DataFrame({
            # convert dates->str. This is the only slow part of this module.
            col: return_series.index.strftime(time_format).values,
            return_series.name: return_series.values,
        })

        return output
