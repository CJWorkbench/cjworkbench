import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyarrow as pa
from cjwmodule.i18n import I18nMessage
from cjwmodule.testing.i18n import i18n_message

from filter import migrate_params, render


def EQ(column: str, value: int):
    return dict(operation="number_is", column=column, value=value)


def _migrated_params(
    column: str,
    operation: str,
    value: str,
    case_sensitive: bool = False,
    regex: bool = False,
    keep: bool = True,
) -> Dict[str, Any]:
    return {
        "keep": keep,
        "condition": {
            "operation": "and",
            "conditions": [
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": operation,
                            "column": column,
                            "value": value,
                            "isCaseSensitive": case_sensitive,
                            "isRegex": regex,
                        }
                    ],
                }
            ],
        },
    }


def test_migrate_v0_select_stays_select():
    assert (
        migrate_params(
            {
                "column": "A",
                "condition": 0,  # "Select" (the default)
                "value": "value",
                "casesensitive": False,
                "keep": 0,  # "Keep"
                "regex": False,
            }
        )
        == _migrated_params("A", "", "value")
    )


def test_migrate_v0_text_contains_without_regex_stays_text_contains():
    assert (
        migrate_params(
            {
                "column": "A",
                "condition": 2,  # "Text contains"
                "value": "value",
                "casesensitive": False,
                "keep": 0,  # "Keep"
                "regex": False,
            }
        )
        == _migrated_params("A", "text_contains", "value")
    )


def test_migrate_v0_text_contains_regex():
    assert (
        migrate_params(
            {
                "column": "A",
                "condition": 2,  # "Text contains"
                "value": "value",
                "casesensitive": False,
                "keep": 0,  # "Keep"
                "regex": True,
            }
        )
        == _migrated_params("A", "text_contains", "value", regex=True)
    )


def test_migrate_v0_cell_is_empty_changes_number():
    assert (
        migrate_params(
            {
                "column": "A",
                "condition": 6,  # "Cell is empty"
                "value": "value",
                "casesensitive": False,
                "keep": 0,  # "Keep"
                "regex": True,
            }
        )
        == _migrated_params("A", "cell_is_null", "value")
    )


def test_migrate_v0_from_dropdown():
    assert migrate_params({"column": "A"}) == _migrated_params("A", "", "")


def test_migrate_v2_keep_0_means_true():
    assert migrate_params(
        {"keep": 0, "filters": {"operator": "and", "filters": []}}
    ) == {"keep": True, "condition": {"operation": "and", "conditions": []}}


def test_migrate_v2_keep_1_means_false():
    assert migrate_params(
        {"keep": 1, "filters": {"operator": "and", "filters": []}}
    ) == {"keep": False, "condition": {"operation": "and", "conditions": []}}


def test_migrate_v3():
    assert migrate_params(
        {"keep": True, "filters": {"operator": "and", "filters": []}}
    ) == {"keep": True, "condition": {"operation": "and", "conditions": []}}


def test_migrate_v3_cell_is_empty_becomes_cell_is_null():
    assert (
        migrate_params(
            {
                "keep": True,
                "filters": {
                    "operator": "and",
                    "filters": [
                        {
                            "operator": "and",
                            "subfilters": [
                                {
                                    "condition": "cell_is_empty",
                                    "colname": "A",
                                    "case_sensitive": False,
                                    "value": "",
                                }
                            ],
                        }
                    ],
                },
            }
        )
        == _migrated_params("A", "cell_is_null", "")
    )


def test_migrate_v4():
    assert migrate_params(
        {"keep": True, "condition": {"operation": "and", "conditions": []}}
    ) == {"keep": True, "condition": {"operation": "and", "conditions": []}}


def _test_render(
    arrow_table: pa.Table,
    params: Dict[str, Any],
    expected_table: Optional[pa.Table],
    expected_errors: List[I18nMessage] = [],
):
    with tempfile.NamedTemporaryFile() as tf:
        path = Path(tf.name)
        actual_errors = render(arrow_table, params, path)
        if path.stat().st_size == 0:
            actual_table = None
        else:
            with pa.ipc.open_file(path) as f:
                actual_table = f.read_all()
        assert actual_errors == expected_errors
        if expected_table is None:
            assert actual_table is None
        else:
            assert actual_table is not None
            assert actual_table.column_names == expected_table.column_names
            for output_column, expected_column in zip(
                actual_table.itercolumns(), expected_table.itercolumns()
            ):
                assert output_column.type == expected_column.type
                assert output_column.to_pylist() == expected_column.to_pylist()
                if pa.types.is_dictionary(output_column.type):
                    for output_chunk, expected_chunk in zip(
                        output_column.iterchunks(), expected_column.iterchunks()
                    ):
                        assert (
                            output_chunk.dictionary.to_pylist()
                            == expected_chunk.dictionary.to_pylist()
                        )


def test_no_condition():
    _test_render(
        pa.table({"A": [1]}), {"keep": True, "condition": None}, pa.table({"A": [1]})
    )


def test_keep_true():
    _test_render(
        pa.table({"A": [1, 2], "B": [2, 3]}),
        {"keep": True, "condition": EQ("A", 2)},
        pa.table({"A": [2], "B": [3]}),
    )


def test_keep_false():
    _test_render(
        pa.table({"A": [1, 2], "B": [2, 3]}),
        {"keep": False, "condition": EQ("A", 2)},
        pa.table({"A": [1], "B": [2]}),
    )


def test_shrink_filtered_dictionary():
    _test_render(
        pa.table(
            {
                "A": pa.array(["a", "a", "b", "c", "c"]).dictionary_encode(),
                "B": pa.array(["c", "c", "b", "a", "a"]).dictionary_encode(),
            }
        ),
        {
            "keep": True,
            "condition": dict(
                operation="text_is",
                column="A",
                value="a",
                isCaseSensitive=True,
                isRegex=False,
            ),
        },
        pa.table(
            {
                "A": pa.array(["a", "a"]).dictionary_encode(),
                "B": pa.array(["c", "c"]).dictionary_encode(),
            }
        ),
    )


def test_regex_errors():
    _test_render(
        pa.table({"A": ["a"]}),
        {
            "keep": True,
            "condition": dict(
                operation="and",
                conditions=[
                    dict(
                        operation="text_is",
                        column="A",
                        value="*",
                        isCaseSensitive=True,
                        isRegex=True,
                    ),
                    dict(
                        operation="text_is",
                        column="A",
                        value="+",
                        isCaseSensitive=True,
                        isRegex=True,
                    ),
                ],
            ),
        },
        None,
        [
            i18n_message(
                "regexParseError.message",
                {"error": "no argument for repetition operator: *"},
            ),
            i18n_message(
                "regexParseError.message",
                {"error": "no argument for repetition operator: +"},
            ),
        ],
    )
