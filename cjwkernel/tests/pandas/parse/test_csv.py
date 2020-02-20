import contextlib
from pathlib import Path
import unittest
import numpy as np
import pyarrow as pa
from typing import ContextManager, Optional, Union
from cjwkernel.pandas.parse.csv import _parse_csv, ParseCsvResult, ParseCsvWarning
from cjwkernel.tests.util import override_settings, assert_arrow_table_equals
from cjwkernel.util import tempfile_context


def assert_csv_result_equals(actual: ParseCsvResult, expected: ParseCsvResult):
    assert_arrow_table_equals(actual.table, expected.table)
    unittest.TestCase().assertSequenceEqual(actual.warnings, expected.warnings)


def _internal_parse_csv(
    path: Path,
    *,
    encoding: Optional[str] = "utf-8",
    delimiter: Optional[str] = ",",
    has_header: bool = False,
    autoconvert_text_to_numbers: bool = False,
):
    return _parse_csv(
        path,
        encoding=encoding,
        delimiter=delimiter,
        has_header=has_header,
        autoconvert_text_to_numbers=autoconvert_text_to_numbers,
    )


@contextlib.contextmanager
def _temp_csv(data: Union[str, bytes]) -> ContextManager[Path]:
    with tempfile_context(suffix=".csv") as path:
        if isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)
        yield path


class ParseCsvInternalTests(unittest.TestCase):
    def test_empty_csv(self):
        with _temp_csv("") as path:
            result = _internal_parse_csv(path)
        assert_csv_result_equals(result, ParseCsvResult(pa.table({}), []))

    def test_has_header_false(self):
        with _temp_csv("A,B\n1,2\n2,3") as path:
            result = _internal_parse_csv(path, has_header=False)
            assert_csv_result_equals(
                result,
                ParseCsvResult(
                    pa.table(
                        {"Column 1": ["A", "1", "2"], "Column 2": ["B", "2", "3"]}
                    ),
                    [],
                ),
            )

    def test_has_header_true(self):
        with _temp_csv("A,B\na,b\nc,d") as path:
            result = _internal_parse_csv(path, has_header=True)
            assert_csv_result_equals(
                result, ParseCsvResult(pa.table({"A": ["a", "c"], "B": ["b", "d"]}), [])
            )

    def test_autoconvert_text_to_number(self):
        # Column 1: [A, 1, 5, 9] (should not convert)
        # Column 2: [1, 2, x, 10] (should not convert)
        # Column 3: [2, 3, 7, 11] (should convert)
        # Column 4: [3, 4, 8, null] (should convert)
        with _temp_csv("A,1,2,3\n1,2,3,4\n5,x,7.1,8\n9,10,11") as path:
            result = _internal_parse_csv(
                path, has_header=False, autoconvert_text_to_numbers=True
            )
            assert_csv_result_equals(
                result,
                ParseCsvResult(
                    pa.table(
                        {
                            "Column 1": ["A", "1", "5", "9"],
                            "Column 2": ["1", "2", "x", "10"],
                            "Column 3": pa.array([2, 3, 7.1, 11], pa.float64()),
                            "Column 4": pa.array([3, 4, 8, None], pa.int8()),
                        }
                    ),
                    [],
                ),
            )

    def test_autoconvert_text_to_number_after_has_header(self):
        # Column 1: [A, 1, 5, 9] (should not convert)
        with _temp_csv("A\n1\n2\n3") as path:
            result = _internal_parse_csv(
                path, has_header=True, autoconvert_text_to_numbers=True
            )
            assert_csv_result_equals(
                result,
                ParseCsvResult(pa.table({"A": pa.array([1, 2, 3], pa.int8())}), []),
            )

    @override_settings(MAX_DICTIONARY_PYLIST_N_BYTES=0)
    def test_autoconvert_all_empty_is_text(self):
        # A: "a", "a"
        # B: "", ""
        # C: "", null
        with _temp_csv("A,B,C\na,,\na,") as path:
            result = _internal_parse_csv(
                path, has_header=True, autoconvert_text_to_numbers=True
            )
            assert_csv_result_equals(
                result,
                ParseCsvResult(
                    pa.table({"A": ["a", "a"], "B": ["", ""], "C": ["", None]}), []
                ),
            )

    def test_autoconvert_all_null_is_text(self):
        with _temp_csv("A,B\na\nb\nc") as path:
            assert_csv_result_equals(
                _internal_parse_csv(
                    path, has_header=True, autoconvert_text_to_numbers=True
                ),
                ParseCsvResult(
                    pa.table(
                        {
                            "A": ["a", "b", "c"],
                            "B": pa.array([None, None, None], pa.utf8()),
                        }
                    ),
                    [],
                ),
            )

    def test_default_column_headers(self):
        # First row is ['A', '', None]
        with _temp_csv("A,\na,b,c") as path:
            result = _internal_parse_csv(path, has_header=True)
            assert_csv_result_equals(
                result,
                ParseCsvResult(
                    pa.table(
                        {
                            "A": ["a"],
                            "Column 2": ["b"],  # "" => default, 'Column 2'
                            "Column 3": ["c"],  # None => default, 'Column 3'
                        }
                    ),
                    [],
                ),
            )

    def test_rewrite_conflicting_column_headers(self):
        with _temp_csv("A,A,Column 4,\na,b,c,d") as path:
            result = _internal_parse_csv(path, has_header=True)
            assert_csv_result_equals(
                result,
                ParseCsvResult(
                    pa.table(
                        {
                            "A": ["a"],
                            "A 2": ["b"],  # rewritten
                            "Column 4": ["c"],
                            "Column 5": ["d"],  # rewritten
                        }
                    ),
                    [ParseCsvWarning.NumberedColumnNames(2, "A 2")],
                ),
            )

    def test_skip_empty_row(self):
        with _temp_csv("A\n\na") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(pa.table({"A": ["a"]}), []),
            )

    def test_fill_gaps_at_start_with_na(self):
        with _temp_csv(b"A,B\na\nb,c") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(pa.table({"A": ["a", "b"], "B": [None, "c"]}), []),
            )

    def test_allow_empty_str(self):
        with _temp_csv(b"A,B\na,\n,b") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(pa.table({"A": ["a", ""], "B": ["", "b"]}), []),
            )

    def test_detect_character_set(self):
        # tests that `chardet` is invoked
        with _temp_csv("A\nfôo\nbar".encode("windows-1252")) as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, encoding=None, has_header=True),
                ParseCsvResult(pa.table({"A": ["fôo", "bar"]}), []),
            )

    def test_warn_and_replace_on_invalid_encoding(self):
        # tests that `chardet` is invoked
        with _temp_csv("A\nfôo\ncafé".encode("windows-1252")) as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, encoding="utf-8", has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["f�o", "caf�"]}),
                    [
                        ParseCsvWarning.RepairedEncoding(
                            encoding="utf-8",
                            first_invalid_byte=244,
                            first_invalid_byte_position=3,
                        )
                    ],
                ),
            )

    def test_txt_sniff_delimiter(self):
        with _temp_csv("A;B\na,b;c") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, delimiter=None, has_header=True),
                ParseCsvResult(pa.table({"A": ["a,b"], "B": ["c"]}), []),
            )

    def test_txt_sniff_delimiter_not_found(self):
        with _temp_csv("A B\na b c") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, delimiter=None, has_header=True),
                ParseCsvResult(pa.table({"A B": ["a b c"]}), []),
            )

    def test_txt_sniff_delimiter_empty_file(self):
        with _temp_csv("") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, delimiter=None, has_header=True),
                ParseCsvResult(pa.table({}), []),
            )

    def test_encode_dictionary(self):
        with _temp_csv("A,B\na,a\na,b\nb,c\nb,d\nb,d\nb,e") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table(
                        {
                            "A": pa.array(
                                ["a", "a", "b", "b", "b", "b"]
                            ).dictionary_encode(),
                            "B": ["a", "b", "c", "d", "d", "e"],
                        }
                    ),
                    [],
                ),
            )

    def test_do_not_dictionary_encode_nulls(self):
        with _temp_csv("A,B\na\nb\nc") as path:
            assert_csv_result_equals(
                _internal_parse_csv(
                    path, has_header=True, autoconvert_text_to_numbers=False
                ),
                ParseCsvResult(
                    pa.table(
                        {
                            "A": ["a", "b", "c"],
                            "B": pa.array([None, None, None], pa.utf8()),
                        }
                    ),
                    [],
                ),
            )

    def test_dictionary_encode_empty(self):
        # All empty strings => 0 bytes of text data. So Arrow doesn't create
        # a buffer ... and our buffer-size math must account for buf=None.
        with _temp_csv("A,B\n,\n,\n,\n,\n,\n") as path:
            assert_csv_result_equals(
                _internal_parse_csv(
                    path, has_header=True, autoconvert_text_to_numbers=False
                ),
                ParseCsvResult(
                    pa.table(
                        {
                            "A": pa.array(["", "", "", "", ""]).dictionary_encode(),
                            "B": pa.array(["", "", "", "", ""]).dictionary_encode(),
                        }
                    ),
                    [],
                ),
            )

    @override_settings(MAX_DICTIONARY_PYLIST_N_BYTES=150)
    def test_do_not_dictionary_encode_if_dictionary_is_too_big(self):
        # no_values dictionary will cost ~200 bytes because Python adds overhead
        no_values = ["A" * 49, "B" * 49] * 50
        # yes_values dictionary will cost ~130 bytes
        yes_values = ["AAA", "BBB"] * 50
        csv = "\n".join(f"{no},{yes}" for no, yes in zip(no_values, yes_values))
        with _temp_csv(csv) as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=False),
                ParseCsvResult(
                    pa.table(
                        {
                            "Column 1": no_values,
                            "Column 2": pa.array(yes_values).dictionary_encode(),
                        }
                    ),
                    [],
                ),
            )

    @override_settings(MIN_DICTIONARY_COMPRESSION_RATIO_PYLIST_N_BYTES=12)
    def test_only_dictionary_encode_for_big_savings(self):
        no_values = ["A", "B", "C"] * 10  # dictionary would give ~10x savings
        yes_values = ["A", "B"] * 15  # dictionary would give ~15x savings
        csv = "\n".join(f"{no},{yes}" for no, yes in zip(no_values, yes_values))
        with _temp_csv(csv) as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=False),
                ParseCsvResult(
                    pa.table(
                        {
                            "Column 1": no_values,
                            "Column 2": pa.array(yes_values).dictionary_encode(),
                        }
                    ),
                    [],
                ),
            )

    @override_settings(MAX_BYTES_PER_VALUE=4)
    def test_truncate_values(self):
        with _temp_csv(
            "\n".join(
                [
                    # Examples from https://en.wikipedia.org/wiki/UTF-8
                    "AAAAxxxx",
                    "AAAA",
                    "AA\u00A2",  # ¢ (2 bytes) -- keep
                    "AAA\u00A2",  # ¢ (2 bytes) -- drop both bytes
                    "A\u0939",  # ह (3 bytes) -- keep
                    "AA\u0939",  # ह (3 bytes) -- drop all three bytes
                    "AAA\u0939",  # ह (3 bytes) -- drop all three bytes
                    "\U00010348",  # 𐍈 (4 bytes) -- keep
                    "A\U00010348",  # 𐍈 (4 bytes) -- drop all four bytes
                    "AA\U00010348",  # 𐍈 (4 bytes) -- drop all four bytes
                    "AAA\U00010348",  # 𐍈 (4 bytes) -- drop all four bytes
                ]
            )
        ) as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table(
                        {
                            "AAAA": [
                                "AAAA",
                                "AA\u00A2",
                                "AAA",
                                "A\u0939",
                                "AA",
                                "AAA",
                                "\U00010348",
                                "A",
                                "AA",
                                "AAA",
                            ]
                        }
                    ),
                    [ParseCsvWarning.TruncatedValues(7, 4, 0, 0)],
                ),
            )

    def test_repair_missing_quote(self):
        with _temp_csv('A,B\n"x" y,"z""" a') as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["x y"], "B": ['z" a']}),
                    [ParseCsvWarning.RepairedValues(2, 1, 0)],
                ),
            )

    def test_repair_unexpected_eof(self):
        with _temp_csv('A,B\nx,"y\nz') as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["x"], "B": ["y\nz"]}),
                    [ParseCsvWarning.RepairedEndOfFile()],
                ),
            )

    def test_tsv(self):
        with _temp_csv("A\tB\na\tb") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True, delimiter="\t"),
                ParseCsvResult(pa.table({"A": ["a"], "B": ["b"]}), []),
            )

    @override_settings(MAX_ROWS_PER_TABLE=5)
    def test_too_many_rows(self):
        with _temp_csv("A\na\nb\nc\nd\ne\nf\ng") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": list("abcd")}), [ParseCsvWarning.SkippedRows(3, 5)]
                ),
            )

    @override_settings(MAX_COLUMNS_PER_TABLE=2)
    def test_too_many_columns(self):
        with _temp_csv("A,B,C,D,E,F\na,b,c,d,e,f") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["a"], "B": ["b"]}),
                    [ParseCsvWarning.SkippedColumns(4, 2)],
                ),
            )

    @override_settings(MAX_CSV_BYTES=13)
    def test_truncate_csv(self):
        with _temp_csv("A,B\na,b\nc,d\ne,f\ng,h") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["a", "c", "e"], "B": ["b", "d", None]}),
                    [ParseCsvWarning.TruncatedFile(19, 13)],
                ),
            )

    @override_settings(MAX_CSV_BYTES=13)
    def test_truncate_csv_repair_utf8(self):
        with _temp_csv("A,B\na,b\nc,d\né,f\ng,h") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"A": ["a", "c", "�"], "B": ["b", "d", None]}),
                    [
                        ParseCsvWarning.TruncatedFile(20, 13),
                        ParseCsvWarning.RepairedEncoding(
                            encoding="utf-8",
                            first_invalid_byte=195,
                            first_invalid_byte_position=12,
                        ),
                    ],
                ),
            )

    def test_has_header_when_n_rows_is_1(self):
        with _temp_csv("A,B") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table(
                        {"A": pa.array([], pa.utf8()), "B": pa.array([], pa.utf8())}
                    ),
                    [],
                ),
            )

    def test_has_header_when_n_rows_is_0(self):
        with _temp_csv("") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(pa.table({}), []),
            )

    def test_n_rows_is_0(self):
        with _temp_csv("") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=False),
                ParseCsvResult(pa.table({}), []),
            )

    def test_omit_ascii_control_characters_from_column_names(self):
        with _temp_csv("A\tB,C\na\tb,c") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table({"AB": ["a\tb"], "C": ["c"]}),
                    [ParseCsvWarning.CleanedAsciiColumnNames(1, "AB")],
                ),
            )

    @override_settings(MAX_BYTES_PER_COLUMN_NAME=4)
    def test_truncate_column_names(self):
        with _temp_csv("ABC,ABCD,ABCDE,BCDEF\na,b,c,d") as path:
            assert_csv_result_equals(
                _internal_parse_csv(path, has_header=True),
                ParseCsvResult(
                    pa.table(
                        {"ABC": ["a"], "ABCD": ["b"], "AB 2": ["c"], "BCDE": ["d"]}
                    ),
                    [
                        ParseCsvWarning.TruncatedColumnNames(2, "AB 2"),
                        ParseCsvWarning.NumberedColumnNames(1, "AB 2"),
                    ],
                ),
            )
