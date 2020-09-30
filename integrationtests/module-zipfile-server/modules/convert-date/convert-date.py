from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

import pandas as pd
from cjwmodule import i18n
from pandas.api.types import is_numeric_dtype


class InputFormat(Enum):
    AUTO = "auto"
    US = "us"
    EU = "eu"

    @property
    def kwargs(self):
        return {
            InputFormat.AUTO: {"infer_datetime_format": True, "format": None},
            InputFormat.US: {"infer_datetime_format": False, "format": "%m/%d/%Y"},
            InputFormat.EU: {"infer_datetime_format": False, "format": "%d/%m/%Y"},
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

    def __add__(self, rhs: "ErrorCount") -> "ErrorCount":
        """Add more errors to this ErrorCount."""
        if self.total == 0:
            return rhs
        else:
            return replace(
                self,
                total=self.total + rhs.total,
                n_columns=self.n_columns + rhs.n_columns,
            )

    @property
    def i18n_message(self):
        return i18n.trans(
            "ErrorCount.message",
            "“{a_value}” in row {a_row} of “{a_column}” cannot be converted. "
            "{n_errors, plural, "
            "  one {Overall, there is # error in {n_columns, plural, other {# columns} one {# column}}.} "
            "  other {Overall, there are # errors in {n_columns, plural, other {# columns} one {# column}}.} "
            "} "
            "Select 'non-dates to null' to set these values to null.",
            {
                "a_value": self.a_value,
                "a_row": self.a_row + 1,
                "a_column": self.a_column,
                "n_errors": self.total,
                "n_columns": self.n_columns,
            },
        )

    def __len__(self):
        """
        Count errors. 0 (which means __bool__ is false) if there are none.
        """
        return self.total

    @staticmethod
    def from_diff(in_series, out_series) -> "ErrorCount":
        in_na = in_series.isna()
        out_na = out_series.isna()
        out_errors = out_na.index[out_na & ~in_na]

        if out_errors.empty:
            return ErrorCount()
        else:
            column = in_series.name
            row = int(out_errors[0])
            value = in_series[row]
            return ErrorCount(column, row, value, len(out_errors), 1)


def render(table, params):
    # No processing if no columns selected
    if not params["colnames"]:
        return table

    input_format = InputFormat(params["input_format"])

    error_count = ErrorCount()

    for column in params["colnames"]:
        in_series = table[column]

        kwargs = {**input_format.kwargs}

        if is_numeric_dtype(in_series):
            # For now, assume value is year and cast to string
            kwargs["format"] = "%Y"

        # Build `out_series`, a pd.Series of datetime64[ns]
        if hasattr(in_series, "cat"):
            # Pandas `to_datetime()` sometimes converts to Categorical; and
            # when it does, `series.dt.tz_localize()` doesn't unwrap the
            # Categorical. We can't blame `to_datetime()` for returning a
            # Categorical but we _can_ blame `.dt.tz_localize()` for not
            # unwrapping it.
            #
            # The bug: https://github.com/pandas-dev/pandas/issues/27952
            #
            # Workaround is to basically do what `pd.to_datetime()` does
            # with its cache, using the assumption that categories are unique.
            # We `tz_localize()` before caching, for speedup.
            #
            # Nix this if-statement and code path when the Pandas bug is fixed.
            text_values = in_series.cat.categories
            date_values = pd.to_datetime(
                text_values,
                errors="coerce",
                exact=False,
                cache=False,
                utc=True,
                **kwargs,
            ).tz_localize(None)
            mapping = pd.Series(date_values, index=text_values)
            out_series = in_series.map(mapping).astype("datetime64[ns]")
        else:
            out_series = pd.to_datetime(
                in_series, errors="coerce", exact=False, cache=True, utc=True, **kwargs
            ).dt.tz_localize(None)

        if not params["error_means_null"]:
            error_count += ErrorCount.from_diff(in_series, out_series)

        table[column] = out_series

    if error_count:
        return error_count.i18n_message

    return table


def _migrate_params_v0_to_v1(params):
    """
    v0: 'type_null' (bool), 'type_date' (input format AUTO|US|EU index)

    v1: 'error_means_null' (bool), 'input_format' (enum 'auto'|'us'|'eu')
    """
    return {
        "colnames": params["colnames"],
        "error_means_null": params["type_null"],
        "input_format": ["auto", "us", "eu"][params["type_date"]],
    }


def _migrate_params_v1_to_v2(params):
    """
    v1: 'colnames' (str comma-delimited)

    v2: 'colnames' (List[str])

    https://www.pivotaltracker.com/story/show/160463316
    """
    return {**params, "colnames": [c for c in params["colnames"].split(",") if c]}


def migrate_params(params):
    if "type_date" in params:
        params = _migrate_params_v0_to_v1(params)
    if isinstance(params["colnames"], str):
        params = _migrate_params_v1_to_v2(params)

    return params
