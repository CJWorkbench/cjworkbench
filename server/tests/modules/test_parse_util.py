from pathlib import Path
from django.test import SimpleTestCase, override_settings
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules import upload
from server.tests.utils import mock_xlsx_path, MockPath


class ParseUtilTest(SimpleTestCase):
    def test_parse_empty_csv(self):
        result = upload.parse_file(MockPath(['x.csv'], b''), True)
        self.assertEqual(result, 'This file is empty')

    def test_parse_has_header_true(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,b'), True)
        assert_frame_equal(result, pd.DataFrame({'A': ['a'], 'B': ['b']}))

    def test_parse_has_header_false(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\n1,2'), False)
        assert_frame_equal(result, pd.DataFrame({
            'Column 1': ['A', '1'],
            'Column 2': ['B', '2'],
        }))

    def test_parse_skip_empty_row(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A\n\na'), True)
        assert_frame_equal(result, pd.DataFrame({'A': ['a']}))

    def test_parse_fill_gaps_at_start_with_na(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na\nb,c'),
                                   True)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'b'],
            'B': [np.nan, 'c'],
        }))

    def test_parse_default_column_headers(self):
        # First row is ['A', '', None]
        result = upload.parse_file(MockPath(['x.csv'], b'A,""\na,b,c'), True)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a'],
            'Column 2': ['b'],  # "" => default, 'Column 2'
            'Column 3': ['c'],  # None => default, 'Column 3'
        }))

    def test_rewrite_conflicting_column_headers(self):
        result = upload.parse_file(
            # Columns 1 and 2 both have name, 'A'
            # Columns 3 and 4 (defaulted) both have name, 'Column 4'
            MockPath(['x.csv'], b'A,A,Column 4,\na,b,c,d'),
            True
        )
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a'],
            'A 2': ['b'],  # rewritten
            'Column 4': ['c'],
            'Column 5': ['d'],  # rewritten
        }))

    def test_parse_fill_gaps_at_middle_with_na(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,b\nc\nd,e'),
                                   True)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'c', 'd'],
            'B': ['b', np.nan, 'e'],
        }))

    def test_parse_fill_gaps_at_end_with_na(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,b\nc,d\ne'),
                                   True)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', 'c', 'e'],
            'B': ['b', 'd', np.nan],
        }))

    def test_parse_csv_allow_empty_str(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,\n,b'), True)
        assert_frame_equal(result, pd.DataFrame({
            'A': ['a', ''],
            'B': ['', 'b'],
        }))

    def test_parse_csv_detect_character_set(self):
        # tests that `chardet` is invoked
        csv = 'A\nfôo\nbar'.encode('windows-1252')
        result = upload.parse_file(MockPath(['x.csv'], csv), True)
        assert_frame_equal(result, pd.DataFrame({'A': ['fôo', 'bar']}))

    def test_parse_txt_sniff_delimiter(self):
        result = upload.parse_file(MockPath(['x.txt'], b'A;B\na,b;c'), True)
        assert_frame_equal(result, pd.DataFrame({'A': ['a,b'], 'B': ['c']}))

    def test_parse_autocast_numbers(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\n1,2.0\n3,4.1'),
                                   True)
        assert_frame_equal(result,
                           pd.DataFrame({'A': [1, 3], 'B': [2.0, 4.1]}))

    def test_parse_auto_categorize(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,a\na,b\nb,c'),
                                   True)
        assert_frame_equal(result, pd.DataFrame({
            # 'a', 'a', 'b' has repeated strings, so we categorize
            'A': pd.Series(['a', 'a', 'b'], dtype='category'),
            'B': pd.Series(['a', 'b', 'c'], dtype=str)
        }))

    def test_parse_csv_repair_errors(self):
        # It would be great to report "warnings" on invalid input. But Python's
        # `csv` module won't do that: it forces us to choose between mangling
        # input and raising an exception. Both are awful; mangling input is
        # slightly preferable, so that's what we do.
        result = upload.parse_file(
            # CSV errors:
            #
            # * Data after close-quote: mangle by appending
            # * Unclosed quote: mangle by auto-closing
            MockPath(['x.csv'], b'A,B\n"x" y,"foo\nB'),
            True
        )
        assert_frame_equal(result,
                           pd.DataFrame({'A': ['x y'], 'B': ['foo\nB']}))

    def test_parse_tsv(self):
        result = upload.parse_file(MockPath(['x.tsv'], b'A\tB\na\tb'), True)
        assert_frame_equal(result, pd.DataFrame({'A': ['a'], 'B': ['b']}))

    def test_parse_xlsx(self):
        path = Path(mock_xlsx_path)
        result = upload.parse_file(path, True)
        assert_frame_equal(result, pd.DataFrame({
            'Month': ['Jan', 'Feb'],
            'Amount': [10, 20]
        }))

    def test_parse_xls(self):
        path = (Path(__file__).parent.parent / 'test_data' / 'example.xls')
        result = upload.parse_file(path, True)
        assert_frame_equal(result, pd.DataFrame({
            'foo': [1, 2],
            'bar': [2, 3],
        }))

    def test_parse_invalid_mime_type(self):
        result = upload.parse_file(MockPath(['x.bin'], b'A'), True)
        self.assertEqual(result, (
            "Unknown file extension '.bin'. Please upload a different file."
        ))

    def test_parse_invalid_xlsx(self):
        result = upload.parse_file(MockPath(['x.xlsx'], b'not an xlsx'), True)
        self.assertEqual(result, (
            'Error reading Excel file: Unsupported format, '
            "or corrupt file: Expected BOF record; found b'not an x'"
        ))

    @override_settings(MAX_ROWS_PER_TABLE=2)
    def test_parse_too_many_rows(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A\na\nb\nc'), False)
        self.assertEqual(result['error'],
                         'The input was too large, so we removed 2 rows')
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'Column 1': ['A', 'a']}))

    @override_settings(MAX_COLUMNS_PER_TABLE=2)
    def test_parse_too_many_columns(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B,C,D\na,b,c,d'),
                                   True)
        self.assertEqual(result['error'], (
            'The input had too many columns, so we removed 2 columns'
        ))
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'A': ['a'], 'B': ['b']}))

    @override_settings(MAX_BYTES_PER_TABLE=290)
    def test_parse_too_many_bytes(self):
        result = upload.parse_file(MockPath(['x.csv'], b'A,B\na,b\nc,d\ne,f'),
                                   True)
        self.assertEqual(result['error'],
                         'The input was too large, so we removed 2 rows')
        assert_frame_equal(result['dataframe'],
                           pd.DataFrame({'A': ['a'], 'B': ['b']}))
