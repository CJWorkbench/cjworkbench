from pathlib import Path
import unittest
from django.test import SimpleTestCase, override_settings
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.parse_util import parse_file
from cjwstate.tests.utils import mock_xlsx_path, MockPath


EmptyDataFrame = pd.DataFrame().reset_index(drop=True)


class ParseTableTests(SimpleTestCase):
    def test_parse_empty_csv(self):
        result = parse_file(MockPath(["x.csv"], b""), True)
        self.assertEqual(result, "This file is empty")

    def test_parse_has_header_true(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,b"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a"], "B": ["b"]}))

    def test_parse_has_header_false(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\n1,2"), False)
        assert_frame_equal(
            result, pd.DataFrame({"Column 1": ["A", "1"], "Column 2": ["B", "2"]})
        )

    def test_parse_skip_empty_row(self):
        result = parse_file(MockPath(["x.csv"], b"A\n\na"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a"]}))

    def test_parse_fill_gaps_at_start_with_na(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na\nb,c"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a", "b"], "B": [np.nan, "c"]}))

    def test_parse_default_column_headers(self):
        # First row is ['A', '', None]
        result = parse_file(MockPath(["x.csv"], b'A,""\na,b,c'), True)
        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    "A": ["a"],
                    "Column 2": ["b"],  # "" => default, 'Column 2'
                    "Column 3": ["c"],  # None => default, 'Column 3'
                }
            ),
        )

    def test_rewrite_conflicting_column_headers(self):
        result = parse_file(
            # Columns 1 and 2 both have name, 'A'
            # Columns 3 and 4 (defaulted) both have name, 'Column 4'
            MockPath(["x.csv"], b"A,A,Column 4,\na,b,c,d"),
            True,
        )
        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    "A": ["a"],
                    "A 2": ["b"],  # rewritten
                    "Column 4": ["c"],
                    "Column 5": ["d"],  # rewritten
                }
            ),
        )

    def test_parse_fill_gaps_at_middle_with_na(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,b\nc\nd,e"), True)
        assert_frame_equal(
            result, pd.DataFrame({"A": ["a", "c", "d"], "B": ["b", np.nan, "e"]})
        )

    def test_parse_fill_gaps_at_end_with_na(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,b\nc,d\ne"), True)
        assert_frame_equal(
            result, pd.DataFrame({"A": ["a", "c", "e"], "B": ["b", "d", np.nan]})
        )

    def test_parse_csv_allow_empty_str(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,\n,b"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a", ""], "B": ["", "b"]}))

    def test_parse_csv_detect_character_set(self):
        # tests that `chardet` is invoked
        csv = "A\nfôo\nbar".encode("windows-1252")
        result = parse_file(MockPath(["x.csv"], csv), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["fôo", "bar"]}))

    def test_parse_txt_sniff_delimiter(self):
        result = parse_file(MockPath(["x.txt"], b"A;B\na,b;c"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a,b"], "B": ["c"]}))

    def test_parse_txt_sniff_delimiter_not_found(self):
        result = parse_file(MockPath(["x.txt"], b"A B\na b c"), True)
        assert_frame_equal(result, pd.DataFrame({"A B": ["a b c"]}))

    def test_parse_txt_sniff_delimiter_empty_file(self):
        result = parse_file(MockPath(["x.txt"], b""), False)
        self.assertEqual(result, "This file is empty")

    def test_parse_autocast_numbers(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\n1,2.0\n3,4.1"), True)
        assert_frame_equal(result, pd.DataFrame({"A": [1, 3], "B": [2.0, 4.1]}))

    def test_parse_auto_categorize(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,a\na,b\nb,c"), True)
        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    # 'a', 'a', 'b' has repeated strings, so we categorize
                    "A": pd.Series(["a", "a", "b"], dtype="category"),
                    "B": pd.Series(["a", "b", "c"], dtype=str),
                }
            ),
        )

    def test_parse_csv_repair_errors(self):
        # It would be great to report "warnings" on invalid input. But Python's
        # `csv` module won't do that: it forces us to choose between mangling
        # input and raising an exception. Both are awful; mangling input is
        # slightly preferable, so that's what we do.
        result = parse_file(
            # CSV errors:
            #
            # * Data after close-quote: mangle by appending
            # * Unclosed quote: mangle by auto-closing
            MockPath(["x.csv"], b'A,B\n"x" y,"foo\nB'),
            True,
        )
        assert_frame_equal(result, pd.DataFrame({"A": ["x y"], "B": ["foo\nB"]}))

    def test_parse_tsv(self):
        result = parse_file(MockPath(["x.tsv"], b"A\tB\na\tb"), True)
        assert_frame_equal(result, pd.DataFrame({"A": ["a"], "B": ["b"]}))

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_parse_too_many_rows(self):
        result = parse_file(MockPath(["x.csv"], b"A\na\nb\nc"), False)
        self.assertEqual(
            result["error"], "The input was too large, so we removed 2 rows"
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame({"Column 1": ["A", "a"]}))

    @override_settings(MAX_COLUMNS_PER_TABLE=2)
    def test_parse_too_many_columns(self):
        result = parse_file(MockPath(["x.csv"], b"A,B,C,D\na,b,c,d"), True)
        self.assertEqual(
            result["error"], ("The input had too many columns, so we removed 2 columns")
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame({"A": ["a"], "B": ["b"]}))

    @override_settings(MAX_BYTES_PER_TABLE=290)
    def test_parse_too_many_bytes(self):
        result = parse_file(MockPath(["x.csv"], b"A,B\na,b\nc,d\ne,f"), True)
        self.assertEqual(
            result["error"], "The input was too large, so we removed 2 rows"
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame({"A": ["a"], "B": ["b"]}))


class ParseJsonTests(SimpleTestCase):
    def _parse_json(self, b: bytes):
        return parse_file(MockPath(["x.json"], b), False)

    def test_json_with_nulls(self):
        result = self._parse_json(
            b"""[
            {"A": "a"},
            {"A": "a"},
            {"A": null}
        ]"""
        )
        expected = pd.DataFrame({"A": ["a", "a", None]}, dtype="category")
        assert_frame_equal(result, expected)

    def test_json_with_int_nulls(self):
        result = self._parse_json(
            b"""[
            {"A": 1},
            {"A": null}
        ]"""
        )
        expected = pd.DataFrame({"A": [1.0, np.nan]})
        assert_frame_equal(result, expected)

    def test_json_str_numbers_are_str(self):
        """JSON input data speficies whether we're String and Number."""
        result = self._parse_json(
            b"""[
            {"A": "1"},
            {"A": "2"}
        ]"""
        )
        expected = pd.DataFrame({"A": ["1", "2"]})
        assert_frame_equal(result, expected)

    def test_json_int64(self):
        """Support int64 -- like Twitter IDs."""
        result = self._parse_json(
            b"""[
            {"A": 1093943422262697985}
        ]"""
        )
        expected = pd.DataFrame({"A": [1093943422262697985]})
        assert_frame_equal(result, expected)

    def test_json_mixed_types_are_str(self):
        """Support int64 -- like Twitter IDs."""
        result = self._parse_json(
            b"""[
            {"A": 1},
            {"A": "2"}
        ]"""
        )
        expected = pd.DataFrame({"A": ["1", "2"]})
        self.assertEqual(
            result["error"], 'Column "A" was mixed-type; we converted it to text.'
        )
        assert_frame_equal(result["dataframe"], expected)

    def test_json_str_dates_are_str(self):
        """JSON does not support dates."""
        result = self._parse_json(
            b"""[
            {"date": "2019-02-20"},
            {"date": "2019-02-21"}
        ]"""
        )
        expected = pd.DataFrame({"date": ["2019-02-20", "2019-02-21"]})
        assert_frame_equal(result, expected)

    def test_json_bools_become_str(self):
        """Workbench does not support booleans; use True/False."""
        # Support null, too -- don't overwrite it.
        result = self._parse_json(
            b"""[
            {"A": true},
            {"A": false},
            {"A": null}
        ]"""
        )
        expected = pd.DataFrame({"A": ["true", "false", np.nan]}, dtype="category")
        assert_frame_equal(result, expected)

    def test_object_becomes_str(self):
        result = self._parse_json(b"""[{"A": {"foo":"bar"}}]""")
        assert_frame_equal(result, pd.DataFrame({"A": ['{"foo":"bar"}']}))

    def test_array_becomes_str(self):
        result = self._parse_json(b"""[{"A": ["foo", "bar"]}]""")
        assert_frame_equal(result, pd.DataFrame({"A": ['["foo","bar"]']}))

    def test_json_encode_nested_arrays_and_objects(self):
        result = self._parse_json(
            b"""[
            {"value": {
                "x": ["y", {"z": true, "Z": ["a", null]}, ["b", "c"] ],
                "X": {}
            }}
        ]"""
        )
        assert_frame_equal(
            result,
            pd.DataFrame(
                {"value": ['{"x":["y",{"z":true,"Z":["a",null]},["b","c"]],"X":{}}']}
            ),
        )

    def test_json_with_undefined(self):
        result = self._parse_json(
            b"""[
            {"A": "a", "C": "c"},
            {"A": "aa", "B": "b"},
            {"C": "cc"}
        ]"""
        )
        assert_frame_equal(
            result,
            pd.DataFrame(
                {
                    "A": ["a", "aa", np.nan],
                    "C": ["c", np.nan, "cc"],
                    "B": [np.nan, "b", np.nan],
                }
            ),
        )

    def test_json_not_records(self):
        result = self._parse_json(b'["foo", "bar"]}')
        self.assertEqual(
            result["error"],
            (
                "Workbench cannot import this JSON file. The JSON file must "
                "be an Array of Objects for Workbench to import it."
            ),
        )
        assert_frame_equal(result["dataframe"], EmptyDataFrame)

    def test_json_not_array(self):
        result = self._parse_json(b'{"meta":{"foo":"bar"},"data":[]}')
        self.assertEqual(
            result["error"],
            (
                "Workbench cannot import this JSON file. The JSON file "
                "must be an Array of Objects for Workbench to import it."
            ),
        )
        assert_frame_equal(result["dataframe"], EmptyDataFrame)

    def test_json_syntax_error(self):
        result = self._parse_json(b"not JSON")
        self.assertEqual(
            result["error"], ("JSON lexical error: invalid string in json text.")
        )
        assert_frame_equal(result["dataframe"], EmptyDataFrame)

    def test_json_reencode_to_utf8(self):
        # result = self._parse_json('[{"x":"€ café"}]'.encode('iso-8859-15'))
        # assert_frame_equal(result, pd.DataFrame({'x': ['€ café']}))
        result = self._parse_json('[{"x":"café"}]'.encode("latin-1"))
        assert_frame_equal(result, pd.DataFrame({"x": ["café"]}))

    def test_json_empty(self):
        result = self._parse_json(b"[]")
        assert_frame_equal(result, EmptyDataFrame)

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_parse_too_many_rows(self):
        result = self._parse_json(b'[{"A":"a"},{"A":"b"},{"A":"c"}]')
        self.assertEqual(
            result["error"], "The input had too many rows, so we removed rows."
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame({"A": ["a", "b"]}))

    @override_settings(MAX_COLUMNS_PER_TABLE=2)
    def test_parse_too_many_columns(self):
        result = self._parse_json(
            b"""[
            {"A": "a", "B": "b", "C":"c"},
            {"A": "aa", "B": "bb"}
        ]"""
        )
        self.assertEqual(
            result["error"], ("The input had too many columns, so we removed some.")
        )
        assert_frame_equal(
            result["dataframe"], pd.DataFrame({"A": ["a", "aa"], "B": ["b", "bb"]})
        )

    @override_settings(MAX_BYTES_PER_TABLE=220)
    def test_parse_too_many_bytes(self):
        result = self._parse_json(
            b"""[
            {"A": "a", "B": "b"},
            {"A": "c", "B": "d"},
            {"A": "e", "B": "f"}
        ]"""
        )
        self.assertEqual(
            result["error"],
            (
                "The input was too large, so we stopped before reading the whole "
                "file."
            ),
        )
        assert_frame_equal(
            result["dataframe"], pd.DataFrame({"A": ["a", "c"], "B": ["b", np.nan]})
        )


class ParseOtherTests(unittest.TestCase):
    def test_parse_xlsx(self):
        path = Path(mock_xlsx_path)
        result = parse_file(path, True)
        assert_frame_equal(
            result, pd.DataFrame({"Month": ["Jan", "Feb"], "Amount": [10, 20]})
        )

    def test_parse_xls(self):
        path = Path(__file__).parent.parent / "test_data" / "example.xls"
        result = parse_file(path, True)
        assert_frame_equal(result, pd.DataFrame({"foo": [1, 2], "bar": [2, 3]}))

    def test_parse_invalid_mime_type(self):
        result = parse_file(MockPath(["x.bin"], b"A"), True)
        self.assertEqual(
            result, ("Unknown file extension '.bin'. Please upload a different file.")
        )

    def test_parse_invalid_xlsx(self):
        result = parse_file(MockPath(["x.xlsx"], b"not an xlsx"), True)
        self.assertEqual(
            result,
            (
                "Error reading Excel file: Unsupported format, "
                "or corrupt file: Expected BOF record; found b'not an x'"
            ),
        )
