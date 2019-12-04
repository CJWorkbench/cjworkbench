import contextlib
import json
from pathlib import Path
from typing import Any, ContextManager, Dict, List, Optional, Union
import unittest
import pyarrow
from cjwkernel.pandas.parse.json import _parse_json, ParseJsonResult, ParseJsonWarning
from cjwkernel.tests.util import (
    assert_arrow_table_equals,
    override_settings,
    tempfile_context,
)


def assert_json_result_equals(actual: ParseJsonResult, expected: ParseJsonResult):
    assert_arrow_table_equals(actual.table, expected.table)
    unittest.TestCase().assertSequenceEqual(actual.warnings, expected.warnings)


def _parse_json_file_with_defaults(
    path: Path, *, encoding: Optional[str] = "utf-8"
) -> ParseJsonResult:
    return _parse_json(path, encoding=encoding)


def _parse_json_with_defaults(
    data: Union[Dict[str, Any], List[Any], str, bytes],
    *,
    encoding: Optional[str] = "utf-8",
) -> ParseJsonResult:
    with _temp_json(data) as path:
        return _parse_json_file_with_defaults(path, encoding=encoding)


@contextlib.contextmanager
def _temp_json(
    data: Union[Dict[str, Any], List[Any], str, bytes]
) -> ContextManager[Path]:
    if isinstance(data, list) or isinstance(data, dict):
        data = json.dumps(data)
    if isinstance(data, str):
        data = data.encode("utf-8")
    with tempfile_context(suffix=".json") as path:
        path.write_bytes(data)
        yield path


class ParseJsonTests(unittest.TestCase):
    # Most tests are in https://github.com/CJWorkbench/arrow-tools. The few
    # tests here are "double-checks" and integration tests.

    def test_null_utf8(self):
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":"a"},{"A":"b"},{"A":null}]'),
            ParseJsonResult(pyarrow.table({"A": ["a", "b", None]}), []),
        )

    def test_null_int(self):
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":1},{"A":null}]'),
            ParseJsonResult(
                pyarrow.table({"A": pyarrow.array([1, None], pyarrow.int8())}), []
            ),
        )

    def test_utf8_numbers_are_utf8(self):
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":"1"},{"A":"2"}]'),
            ParseJsonResult(pyarrow.table({"A": ["1", "2"]}), []),
        )

    def test_int64(self):
        # e.g., Twitter IDs
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":1093943422262697985}]'),
            ParseJsonResult(pyarrow.table({"A": [1093943422262697985]}), []),
        )

    def test_utf8_dates_are_utf8(self):
        # JSON does not support dates
        assert_json_result_equals(
            _parse_json_with_defaults('[{"date":"2019-02-20"},{"date":"2019-02-21"}]'),
            ParseJsonResult(pyarrow.table({"date": ["2019-02-20", "2019-02-21"]}), []),
        )

    def test_boolean_becomes_utf8(self):
        # Workbench does not support booleans; use True/False.
        # Support null, too -- don't overwrite it.
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":true},{"A":false},{"A":null}]'),
            ParseJsonResult(pyarrow.table({"A": ["true", "false", None]}), []),
        )

    def test_object_becomes_utf8(self):
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":{"foo": "bar"}}]'),
            ParseJsonResult(pyarrow.table({"A": ['{"foo":"bar"}']}), []),
        )

    def test_array_becomes_utf8(self):
        assert_json_result_equals(
            _parse_json_with_defaults('[{"A":["foo", "bar"]}]'),
            ParseJsonResult(pyarrow.table({"A": ['["foo","bar"]']}), []),
        )

    def test_encode_nested_arrays_and_objects(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                [
                    {
                        "value": {
                            "x": ["y", {"z": True, "Z": ["a", None]}, ["b", "c"]],
                            "X": {},
                        }
                    }
                ]
            ),
            ParseJsonResult(
                pyarrow.table(
                    {
                        "value": [
                            '{"x":["y",{"z":true,"Z":["a",null]},["b","c"]],"X":{}}'
                        ]
                    }
                ),
                [],
            ),
        )

    def test_undefined(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                """
                [
                    {"A": "a", "C": "c"},
                    {"A": "aa", "B": "b"},
                    {"C": "cc"}
                ]
                """
            ),
            ParseJsonResult(
                pyarrow.table(
                    {
                        "A": ["a", "aa", None],
                        "C": ["c", None, "cc"],
                        "B": [None, "b", None],
                    }
                ),
                [],
            ),
        )

    def test_json_not_records(self):
        assert_json_result_equals(
            _parse_json_with_defaults(["foo", "bar"]),
            ParseJsonResult(
                pyarrow.table({}),
                [
                    ParseJsonWarning.TODO_i18n(
                        'skipped 2 non-Object records; example Array item 0: "foo"'
                    )
                ],
            ),
        )

    def test_json_not_array(self):
        assert_json_result_equals(
            _parse_json_with_defaults('"foo"'),
            ParseJsonResult(
                pyarrow.table({}),
                [
                    ParseJsonWarning.TODO_i18n(
                        'JSON is not an Array or Object containing an Array; got: "foo"'
                    )
                ],
            ),
        )

    def test_json_find_subarray(self):
        assert_json_result_equals(
            _parse_json_with_defaults({"meta": {"foo": "bar"}, "data": [{"x": "y"}]}),
            ParseJsonResult(pyarrow.table({"x": ["y"]}), []),
        )

    def test_json_syntax_error(self):
        assert_json_result_equals(
            _parse_json_with_defaults("not JSON"),
            ParseJsonResult(
                pyarrow.table({}),
                [
                    ParseJsonWarning.TODO_i18n(
                        "JSON parse error at byte 1: Invalid value."
                    )
                ],
            ),
        )

    def test_json_autodetect_encoding(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                '[{"x": "café"}]'.encode("windows-1252"), encoding=None
            ),
            ParseJsonResult(pyarrow.table({"x": ["café"]}), []),
        )

    def test_json_force_encoding(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                '[{"x": "café"}]'.encode("windows-1252"), encoding="windows-1252"
            ),
            ParseJsonResult(pyarrow.table({"x": ["café"]}), []),
        )

    def test_json_replace_badly_encoded_characters(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                '[{"x": "café"}]'.encode("windows-1252"), encoding="utf-8"
            ),
            ParseJsonResult(
                pyarrow.table({"x": ["caf�"]}),
                [
                    ParseJsonWarning.RepairedEncoding(
                        encoding="utf-8",
                        first_invalid_byte=233,
                        first_invalid_byte_position=11,
                    )
                ],
            ),
        )

    def test_json_empty(self):
        assert_json_result_equals(
            _parse_json_with_defaults("[]"), ParseJsonResult(pyarrow.table({}), [])
        )

    def test_dictionary_encode(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                [{"A": "a", "B": "b"}, {"A": "a", "B": "bb"}, {"A": "a", "B": "bbb"}]
            ),
            ParseJsonResult(
                pyarrow.table(
                    {
                        "A": pyarrow.array(["a", "a", "a"]).dictionary_encode(),
                        "B": ["b", "bb", "bbb"],
                    }
                ),
                [],
            ),
        )

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_max_rows(self):
        assert_json_result_equals(
            _parse_json_with_defaults([{"A": "a"}, {"A": "b"}, {"A": "c"}]),
            ParseJsonResult(
                pyarrow.table({"A": ["a", "b"]}),
                [ParseJsonWarning.TODO_i18n("skipped 1 rows (after row limit of 2)")],
            ),
        )

    @override_settings(MAX_COLUMNS_PER_TABLE=2)
    def test_max_columns(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                [{"A": "a", "B": "b", "C": "c"}, {"A": "aa", "B": "bb"}]
            ),
            ParseJsonResult(
                pyarrow.table({"A": ["a", "aa"], "B": ["b", "bb"]}),
                [
                    ParseJsonWarning.TODO_i18n(
                        "skipped column C (after column limit of 2)"
                    )
                ],
            ),
        )

    @override_settings(MAX_BYTES_TEXT_DATA=8)
    def test_max_bytes_text(self):
        assert_json_result_equals(
            _parse_json_with_defaults(
                [{"A": "abcd", "B": "bcde"}, {"A": "c", "B": "def"}]
            ),
            ParseJsonResult(
                pyarrow.table({"A": ["abcd"], "B": ["bcde"]}),
                [ParseJsonWarning.TODO_i18n("stopped at limit of 8 bytes of data")],
            ),
        )

    @override_settings(MAX_BYTES_PER_COLUMN_NAME=2)
    def test_max_bytes_per_column_name(self):
        assert_json_result_equals(
            _parse_json_with_defaults([{"ABCD": "x", "BCDEFG": "y"}]),
            ParseJsonResult(
                pyarrow.table({"AB": ["x"], "BC": ["y"]}),
                [ParseJsonWarning.TODO_i18n("truncated 2 column names; example AB")],
            ),
        )

    @override_settings(MAX_BYTES_PER_VALUE=3)
    def test_max_bytes_per_value(self):
        assert_json_result_equals(
            _parse_json_with_defaults([{"A": ["abc", "def"], "B": "ghij"}]),
            ParseJsonResult(
                pyarrow.table({"A": ['["a'], "B": ["ghi"]}),
                [
                    ParseJsonWarning.TODO_i18n(
                        "truncated 2 values (value byte limit is 3; see row 0 column A)"
                    )
                ],
            ),
        )
