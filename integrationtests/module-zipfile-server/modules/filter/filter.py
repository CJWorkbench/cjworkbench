from collections import namedtuple
import functools
from typing import Any, Callable, Dict, Optional
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
import re2


class UserVisibleError(Exception):
    """A message for the user. Use str(err) to see it."""

    pass


def str_to_regex(s: str, case_sensitive: bool):
    """
    Convert to regexp, or raise UserVisibleError.
    """
    try:
        # Compile the actual regex, to generate the actual error message.
        r = re2.compile(s)
    except re2.error as err:
        # Handle https://github.com/facebook/pyre2/pull/16
        # Sometimes err.msg is an integer and err.pattern is the actual error
        # message.
        #
        # Nix this when upstream is fixed.
        if isinstance(err.msg, int):
            msg = err.pattern
        else:
            msg = str(err)
        raise UserVisibleError("Regex parse error: %s" % msg)

    if not case_sensitive:
        # case-insensitive: compile _again_ (fb-re2 doesn't support
        # case-insensitive flag; we want the error message to apply to the
        # original pattern because any valid original pattern should be valid
        # here -- otherwise it's a dev error.)
        r = re2.compile(f"(?i:{s})")

    return r


def series_map_predicate(series: pd.Series, pred: Callable[[str], bool]):
    def safe_pred(s: Optional[str]) -> bool:
        # optimization over pd.isna(): just check if it's a str. Any non-str is
        # NA, because this is a str column. And this is faster than pd.isna()
        # because it pd.isna() does ~5 isinstance() tests.
        if isinstance(s, str):
            return pred(s)
        else:
            return False

    return series.map(safe_pred)


def series_to_text(series, strict=False):
    """
    Convert to text, or raise UserVisibleError.

    TODO [adamhooper, 2018-12-19] nix this and quick-fix coltypes
    """
    if hasattr(series, "cat") or series.dtype == object:
        return series
    else:
        raise UserVisibleError("Column is not text. Please convert to text.")


def series_to_number(series):
    """
    Convert to number, or raise UserVisibleError.

    TODO [adamhooper, 2018-12-19] nix this and quick-fix coltypes
    """
    try:
        return pd.to_numeric(series, errors="raise")
    except ValueError:
        raise UserVisibleError("Column is not numbers. Please convert to numbers.")


def value_to_number(value):
    """
    Convert to number, or raise UserVisibleError.
    """
    try:
        return pd.to_numeric(value, errors="raise")
    except ValueError:
        raise UserVisibleError("Value is not a number. Please enter a valid number.")


def series_to_datetime(series):
    """
    Convert to datetime, or raise UserVisibleError.

    TODO [adamhooper, 2018-12-19] nix this and quick-fix coltypes
    """
    try:
        if is_numeric_dtype(series):
            # numeric columns, just... no. Never really want to interpret as
            # seconds since 1970
            raise ValueError("Refusing to convert numbers to dates")

        return pd.to_datetime(series, utc=True)
    except ValueError:
        raise UserVisibleError("Column is not dates. Please convert to dates.")


def value_to_datetime(value):
    """
    Convert to datetime, or raise UserVisibleError.
    """
    try:
        return pd.to_datetime(value, utc=True)
    except ValueError:
        raise UserVisibleError("Value is not a date. Please enter a date and time.")


def type_text(f, strict=False):
    @functools.wraps(f)
    def inner(series, value, *args, **kwargs):
        series = series_to_text(series)  # raises UserVisibleError
        return f(series, value, *args, **kwargs)

    return inner


def type_number(f):
    @functools.wraps(f)
    def inner(series, value, *args, **kwargs):
        series = series_to_number(series)  # raises UserVisibleError
        value = value_to_number(value)  # raises UserVisibleError
        return f(series, value, *args, **kwargs)

    return inner


def type_date(f):
    @functools.wraps(f)
    def inner(series, value, *args, **kwargs):
        series = series_to_datetime(series)  # raises UserVisibleError
        value = value_to_datetime(value)  # raises UserVisibleError
        return f(series, value, *args, **kwargs)

    return inner


@type_text
def mask_text_contains(series, text, case_sensitive):
    # keeprows = matching, not NaN
    contains = series.str.contains(text, case=case_sensitive, regex=False)
    return contains == True  # noqa: E712


@type_text
def mask_text_contains_regex(series, text, case_sensitive):
    r = str_to_regex(text, case_sensitive)
    contains = series_map_predicate(series, r.test_search)
    return contains == True  # noqa: E712


@type_text
def mask_text_does_not_contain(series, text, case_sensitive):
    # keeprows = not matching, allow NaN
    contains = series.str.contains(text, case=case_sensitive, regex=False)
    return contains != True  # noqa: E712


@type_text
def mask_text_does_not_contain_regex(series, text, case_sensitive):
    # keeprows = not matching, allow NaN
    r = str_to_regex(text, case_sensitive)
    contains = series_map_predicate(series, r.test_search)
    return contains != True  # noqa: E712


@type_text
def mask_text_is_exactly(series, text, case_sensitive):
    if case_sensitive:
        return series == text
    else:
        return series.str.lower() == text.lower()


@type_text
def mask_text_is_not_exactly(series, text, case_sensitive):
    if case_sensitive:
        return series != text
    else:
        return series.str.lower() != text.lower()


@type_text
def mask_text_is_exactly_regex(series, text, case_sensitive):
    r = str_to_regex(text, case_sensitive)
    contains = series_map_predicate(series, r.test_fullmatch)
    return contains == True  # noqa: E712


def mask_cell_is_null(series, val, case_sensitive):
    return series.isnull()


def mask_cell_is_not_null(series, val, case_sensitive):
    return ~(series.isnull())


def mask_cell_is_empty(series, val, case_sensitive):
    return (series.isnull()) | (series == "")


def mask_cell_is_not_empty(series, val, case_sensitive):
    if series.dtype == object or hasattr(series, "cat"):
        return ~((series.isnull()) | (series == ""))
    else:
        return ~(series.isnull())


@type_number
def mask_number_equals(series, number, case_sensitive):
    return series == number


@type_number
def mask_number_does_not_equal(series, number, case_sensitive):
    return series != number


@type_number
def mask_number_is_greater_than(series, number, case_sensitive):
    return series > number


@type_number
def mask_number_is_greater_than_or_equals(series, number, case_sensitive):
    return series >= number


@type_number
def mask_number_is_less_than(series, number, case_sensitive):
    return series < number


@type_number
def mask_number_is_less_than_or_equals(series, number, case_sensitive):
    return series <= number


@type_date
def mask_date_is(series, date, case_sensitive):
    return series == date


@type_date
def mask_date_is_not(series, date, case_sensitive):
    return series != date


@type_date
def mask_date_is_before(series, date, case_sensitive):
    return series < date


@type_date
def mask_date_is_after(series, date, case_sensitive):
    return series > date


MaskFunctions = {
    "text_contains": mask_text_contains,
    "text_does_not_contain": mask_text_does_not_contain,
    "text_is_exactly": mask_text_is_exactly,
    "text_is_not_exactly": mask_text_is_not_exactly,
    "text_contains_regex": mask_text_contains_regex,
    "text_does_not_contain_regex": mask_text_does_not_contain_regex,
    "text_is_exactly_regex": mask_text_is_exactly_regex,
    # TODO next migration, do some renames:
    # cell_is_empty => cell_is_null
    # cell_is_not_empty => cell_is_not_null
    # cell_is_empty_str_or_null => cell_is_empty
    # cell_is_not_empty_str_or_null => cell_is_not_empty
    # https://www.pivotaltracker.com/story/show/167466174
    # https://www.pivotaltracker.com/story/show/167467347
    "cell_is_empty": mask_cell_is_null,
    "cell_is_not_empty": mask_cell_is_not_null,
    "cell_is_empty_str_or_null": mask_cell_is_empty,
    "cell_is_not_empty_str_or_null": mask_cell_is_not_empty,
    "number_equals": mask_number_equals,
    "number_does_not_equal": mask_number_does_not_equal,
    "number_is_greater_than": mask_number_is_greater_than,
    "number_is_greater_than_or_equals": mask_number_is_greater_than_or_equals,
    "number_is_less_than": mask_number_is_less_than,
    "number_is_less_than_or_equals": mask_number_is_less_than_or_equals,
    "date_is": mask_date_is,
    "date_is_not": mask_date_is_not,
    "date_is_before": mask_date_is_before,
    "date_is_after": mask_date_is_after,
}


def _migrate_params_v0_to_v1(params: Dict[str, Any]) -> Dict[str, Any]:
    is_regex = params["regex"]
    condition = params["condition"]

    # v0:
    # Select|| (0,1)
    # Text contains|Text does not contain|Text is exactly|| (2, 3, 4, 5)
    # Cell is empty|Cell is not empty|| (6, 7, 8)
    # Equals|Greater than|Greater than or equals|Less than|Less than or
    #   equals|| (9, 10, 11, 12, 13, 14)
    # Date is|Date is before|Date is after (15, 16, 17)
    #
    # v1:
    # Select|| (0,1)
    # Text contains|Text does not contain|Text is exactly|| (2, 3, 4, 5)
    # Text contains regex|Text does not contain regex|Text matches regex
    #   exactly|| (6, 7, 8, 9)
    # Cell is empty|Cell is not empty|| (10, 11, 12)
    # Equals|Greater than|Greater than or equals|Less than|Less than or
    #   equals|| (13, 14, 15, 16, 17, 18)
    # Date is|Date is before|Date is after (19, 20, 21)

    if is_regex and condition in (2, 3, 4, 5):
        condition += 4  # 2 => 6, 3 => 7, ...
    elif condition > 5:
        condition += 4

    ret = dict(params)
    del ret["regex"]
    ret["condition"] = condition
    return ret


def _migrate_params_v1_to_v2(params: Dict[str, Any]) -> Dict[str, Any]:
    # v1 condition _was_ number pointing into menu:
    # Select|| (0,1)
    # Text contains|Text does not contain|Text is exactly|| (2, 3, 4, 5)
    # Text contains regex|Text does not contain regex|Text matches regex
    #   exactly|| (6, 7, 8, 9)
    # Cell is empty|Cell is not empty|| (10, 11, 12)
    # Equals|Greater than|Greater than or equals|Less than|Less than or
    #   equals|| (13, 14, 15, 16, 17, 18)
    # Date is|Date is before|Date is after (19, 20, 21)
    try:
        condition = [
            "",
            "",
            "text_contains",
            "text_does_not_contain",
            "text_is_exactly",
            "",
            "text_contains_regex",
            "text_does_not_contain_regex",
            "text_is_exactly_regex",
            "",
            "cell_is_empty",
            "cell_is_not_empty",
            "",
            "number_equals",
            "number_is_greater_than",
            "number_is_greater_than_or_equals",
            "number_is_less_than",
            "number_is_less_than_or_equals",
            "",
            "date_is",
            "date_is_before",
            "date_is_after",
        ][params.get("condition", 0)]
    except IndexError:
        condition = ""

    return {
        "keep": params.get("keep", 0),
        "filters": {
            "operator": "and",
            "filters": [
                {
                    "operator": "and",
                    "subfilters": [
                        {
                            "colname": params["column"],
                            "condition": condition,
                            "value": params.get("value", ""),
                            "case_sensitive": params.get("casesensitive", False),
                        }
                    ],
                }
            ],
        },
    }


def _migrate_params_v2_to_v3(params):
    # v2: params['keep'] is 0 (True) or 1 (False)
    #
    # v3: params['keep'] is bool
    return {**params, "keep": params["keep"] == 0}


def migrate_params(params: Dict[str, Any]):
    # v0: 'regex' is a checkbox. Migrate it to a menu entry.
    if "regex" in params:
        params = _migrate_params_v0_to_v1(params)

    # v1: just one condition. v2: op+filters, each containing op+subfilters
    if "column" in params:
        params = _migrate_params_v1_to_v2(params)

    # v2: 'keep' is an integer (not a boolean)
    # Don't use `isinstance(params['keep'], int)` because bool is a subclass of
    # int (!)
    if not isinstance(params["keep"], bool):
        params = _migrate_params_v2_to_v3(params)

    return params


Filters = namedtuple("Filters", ("operator", "filters"))
Filter = namedtuple("Filter", ("operator", "subfilters"))
Subfilter = namedtuple("Subfilter", ("colname", "condition", "value", "case_sensitive"))


def parse_filters(operator: str, filters: list) -> Optional[Filters]:
    """
    Filters from input, minus incomplete subfilters.

    If no subfilters are complete, return None.
    """
    parsed_filters = [_parse_filter(**f) for f in filters]
    valid_filters = [f for f in parsed_filters if f is not None]
    if valid_filters:
        return Filters(operator, valid_filters)
    else:
        return None


def _parse_filter(operator: str, subfilters: list) -> Optional[Filter]:
    """
    Filter from input, minus incomplete subfilters.

    If no subfilters are complete, return None.
    """
    parsed_subfilters = [_parse_subfilter(**sf) for sf in subfilters]
    valid_subfilters = [sf for sf in parsed_subfilters if sf is not None]
    if valid_subfilters:
        return Filter(operator, valid_subfilters)
    else:
        return None


def _parse_subfilter(
    colname: str, condition: str, value: str, case_sensitive: bool
) -> Optional[Subfilter]:
    """
    Subfilter from input, or None if invalid.
    """
    if (
        not colname
        or condition not in MaskFunctions
        or (
            not value
            and (
                condition
                not in (
                    "text_is_exactly",
                    "text_is_not_exactly",
                    "cell_is_empty",
                    "cell_is_not_empty",
                    "cell_is_empty_str_or_null",
                    "cell_is_not_empty_str_or_null",
                )
            )
        )
    ):
        return None
    else:
        return Subfilter(colname, condition, value, case_sensitive)


def _merge_masks_mask1_none_is_ok(mask1: np.array, mask2: np.array, op: str):
    if mask1 is None:
        return mask2
    elif op == "and":
        return mask1 & mask2
    else:
        return mask1 | mask2


def _mask_filters(table: pd.DataFrame, filters: Filters) -> np.array:
    """
    Generate boolean mask of table values matching filters.
    """
    mask = None

    operator = filters.operator
    for f in filters.filters:
        if mask is None:
            mask = _mask_filter(table, f)
        else:
            mask2 = _mask_filter(table, f)
            if operator == "and":
                mask = mask & mask2
            else:
                mask = mask | mask2

    return mask


def _mask_filter(table: pd.DataFrame, f: Filter) -> np.array:
    """
    Generate boolean mask of table values matching subfilters.
    """
    mask = None

    op = f.operator
    for subfilter in f.subfilters:
        submask = _mask_subfilter(table, subfilter)
        mask = _merge_masks_mask1_none_is_ok(mask, submask, op)

    return mask


def _mask_subfilter(table: pd.DataFrame, subfilter: Subfilter) -> np.array:
    """
    Generate boolean mask of table values matching subfilter.
    """
    series = table[subfilter.colname]
    func = MaskFunctions[subfilter.condition]
    # raises UserVisibleError
    return func(series, subfilter.value, subfilter.case_sensitive)


def render(table, params):
    filters = parse_filters(**params["filters"])

    if filters is None:
        return table

    try:
        mask = _mask_filters(table, filters)
    except UserVisibleError as err:
        return str(err)

    if not params["keep"]:
        mask = ~mask

    ret = table[mask]
    ret.reset_index(drop=True, inplace=True)

    for column in ret.columns:
        series = ret[column]
        if hasattr(series, "cat"):
            series.cat.remove_unused_categories(inplace=True)

    return ret
