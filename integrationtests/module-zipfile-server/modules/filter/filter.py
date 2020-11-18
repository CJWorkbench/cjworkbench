from typing import Any, Dict

import pyarrow as pa
import pyarrow.compute
from cjwmodule import i18n
from cjwmodule.arrow.condition import ConditionError, condition_to_mask


def _filter_table(arrow_table: pa.Table, params: Dict[str, Any]) -> pa.Table:
    if not params["condition"]:
        return arrow_table

    if params["keep"]:
        condition = params["condition"]
    else:
        condition = {"operation": "not", "condition": params["condition"]}

    mask = condition_to_mask(arrow_table, condition)  # or raise ConditionError
    return pa.table(
        {
            name: pa.compute.filter(column, mask)
            for name, column in zip(arrow_table.column_names, arrow_table.itercolumns())
        }
    )


def render(arrow_table: pa.Table, params, output_path, **kwargs):
    try:
        output_table = _filter_table(arrow_table, params)
    except ConditionError as err:
        return [
            i18n.trans(
                "regexParseError.message",
                "Regex parse error: {error}",
                {"error": e.msg},
            )
            for e in err.errors
        ]

    with pa.ipc.RecordBatchFileWriter(output_path, output_table.schema) as writer:
        writer.write_table(output_table)
    return []


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


def _migrate_params_v3_to_v4(params):
    # v3: "operator+filters", each filter "operator+subfilters", snake_case names
    # v4: nested operations, renamed, regex is boolean option
    filters = params["filters"]

    operations_map = {
        "": "",
        "text_contains": "text_contains",
        "text_does_not_contain": "text_does_not_contain",
        "text_is_exactly": "text_is",
        "text_is_not_exactly": "text_is_not",
        "text_contains_regex": "text_contains",
        "text_does_not_contain_regex": "text_does_not_contain",
        "text_is_exactly_regex": "text_is",
        "cell_is_empty": "cell_is_null",
        "cell_is_not_empty": "cell_is_not_null",
        "cell_is_empty_str_or_null": "cell_is_empty",
        "cell_is_not_empty_str_or_null": "cell_is_not_empty",
        "number_equals": "number_is",
        "number_does_not_equal": "number_is_not",
        "number_is_greater_than": "number_is_greater_than",
        "number_is_greater_than_or_equals": "number_is_greater_than_or_equals",
        "number_is_less_than": "number_is_less_than",
        "number_is_less_than_or_equals": "number_is_less_than_or_equals",
        "date_is": "timestamp_is",
        "date_is_not": "timestamp_is_not",
        "date_is_before": "timestamp_is_before",
        "date_is_after": "timestamp_is_after",
    }

    def migrate_subfilter(subfilter):
        return dict(
            operation=operations_map[subfilter["condition"]],
            column=subfilter["colname"],
            value=subfilter["value"],
            isCaseSensitive=subfilter["case_sensitive"],
            isRegex=subfilter["condition"].endswith("_regex"),
        )

    return {
        "keep": params["keep"],
        "condition": {
            # [2020-11-13] in v3, "condition" is always 2 levels deep
            "operation": filters["operator"],  # and|or
            "conditions": [
                {
                    "operation": filter["operator"],
                    "conditions": [
                        migrate_subfilter(sf) for sf in filter["subfilters"]
                    ],
                }
                for filter in filters["filters"]
            ],
        },
    }


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

    if "filters" in params:
        params = _migrate_params_v3_to_v4(params)

    return params
