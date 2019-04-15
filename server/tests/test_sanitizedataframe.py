import json
import os
from unittest import TestCase
from django.conf import settings
import numpy as np
import pandas as pd
from pandas.util import hash_pandas_object
from pandas.testing import assert_frame_equal
from server.sanitizedataframe import sanitize_dataframe


class SanitizeDataFrameTest(TestCase):
    def test_sanitize_dataframe(self):
        # Load a test table which has a dict column
        fname = os.path.join(settings.BASE_DIR,
                             'server/tests/test_data/sfpd.json')
        sfpd_dict = json.load(open(fname))
        sfpd = pd.DataFrame(sfpd_dict)

        sfpd_types = sfpd.apply(pd.api.types.infer_dtype, skipna=True)
        self.assertEqual(sfpd.columns[6], 'location')
        self.assertEqual(sfpd_types[6], 'mixed')

        sanitize_dataframe(sfpd)

        # should have converted mixed types (and other complex types) to string
        sfpd_types = sfpd.apply(pd.api.types.infer_dtype, skipna=True)
        self.assertEqual(sfpd_types[6], 'string')

    def test_mixed_to_string_keeps_nan(self):
        # check that sanitizing a non-string column with missing data produces
        # empty cells, not 'nan' strings
        # https://www.pivotaltracker.com/story/show/154619564
        result = pd.DataFrame({'A': [1.0, 'str', np.nan, '']})  # mixed
        sanitize_dataframe(result)
        assert_frame_equal(
            result,
            pd.DataFrame({'A': ['1.0', 'str', np.nan, '']})
        )

    def test_mixed_to_string_allows_custom_types(self):
        class Obj:
            def __str__(self):
                return 'x'

        table = pd.DataFrame({'A': [Obj(), Obj()]})
        sanitize_dataframe(table)
        expected = pd.DataFrame({'A': ['x', 'x']})
        assert_frame_equal(table, expected)

    def test_categories_to_string_allows_custom_category_types(self):
        class Obj:
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        table = pd.DataFrame({'A': [Obj('a'), Obj('b'), Obj('a'), 'a', 'y']},
                             dtype='category')
        sanitize_dataframe(table)
        expected = pd.DataFrame({'A': ['a', 'b', 'a', 'a', 'y']},
                                dtype='category')
        assert_frame_equal(table, expected)

    def test_categories_to_string_allows_abnormal_index(self):
        class Obj:
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        # Slicing a DataFrame slices its Series: the category list remains
        # complete, even though some categories aren't used. In this example,
        # `table['A']` has an Obj('a') category, even though the value doesn't
        # appear anywhere in the dataframe. (This is because slicing creates a
        # numpy "view", not a copy of the original array of codes.)
        #
        # Sanitize's output shouldn't include any categories that aren't
        # visible. (The data in memory should not be a "view".)
        table = pd.DataFrame({'A': [Obj('a'), Obj('b'), 'c', 'b']},
                             dtype='category')[1:]
        sanitize_dataframe(table)
        expected = pd.DataFrame({'A': ['b', 'c', 'b']}, dtype='category')
        assert_frame_equal(table, expected)
        self.assertEqual(
            sorted(expected['A'].cat.categories.tolist()),
            ['b', 'c']
        )

    def test_lists_and_dicts(self):
        result = pd.DataFrame({'A': [[5, 6, 7], {'a': 'b'}]})
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': ['[5, 6, 7]', "{'a': 'b'}"]})
        assert_frame_equal(result, expected)

    def test_duplicate_colnames(self):
        # check that duplicate cols are renamed, and that non-string names are
        # converted to string
        result = pd.DataFrame(
            data=[[1, 2, 3, 4, 5], [2, 3, 4, 5, 6], [3, 4, 5, 6, 7]],
            columns=['A', 'B', 'B', 'A', 'A']
        )
        sanitize_dataframe(result)
        expected = pd.DataFrame({
            'A': [1, 2, 3],
            'B': [2, 3, 4],
            'B_1': [3, 4, 5],
            'A_1': [4, 5, 6],
            'A_2': [5, 6, 7],
        })
        assert_frame_equal(result, expected)

    def test_duplicate_colnames_rename_conflict(self):
        # check that duplicate cols are renamed, and that non-string names are
        # converted to string
        result = pd.DataFrame(data=[[1, 2, 3], [2, 3, 4], [3, 4, 5]],
                              columns=['A', 'A_1', 'A'])
        sanitize_dataframe(result)
        expected = pd.DataFrame({
            'A': [1, 2, 3],
            'A_1': [2, 3, 4],
            'A_1_1': [3, 4, 5],
        })
        assert_frame_equal(result, expected)

    def test_nonstr_colnames(self):
        # #157901159: "first row is header" option gives int column name, but
        # Workbench requires str
        result = pd.DataFrame(data=[['a', 'b'], ['c', 'd']],
                              columns=['A', 3])
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': ['a', 'c'], '3': ['b', 'd']})
        assert_frame_equal(result, expected)

    def test_rename_colnames_while_converting_types(self):
        # when we replace a column, there must not be duplicates. In other
        # words: rename-duplicates must come before replace.
        result = pd.DataFrame(data=[['a', {'a': 'b'}], ['c', 'd']],
                              columns=['A', 3])
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': ['a', 'c'], '3': ["{'a': 'b'}", 'd']})
        assert_frame_equal(result, expected)

    def test_reset_index(self):
        # should always come out with row numbers contiguous from zero
        table = pd.DataFrame([[1, 'a'], [2, 'b'], [3, 'c']])
        # lose middle row, makes index non-contiguous
        newtab = pd.concat([table.iloc[0:0], table.iloc[1:]])
        sanitize_dataframe(newtab)
        self.assertCountEqual((newtab.index), [0, 1])

    def test_cast_int_category_to_int(self):
        result = pd.DataFrame({'A': [1, 2]}, dtype='category')
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': [1, 2]})
        assert_frame_equal(result, expected)

    def test_cast_mixed_category_to_str(self):
        result = pd.DataFrame({'A': [1, '2']}, dtype='category')
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': ['1', '2']}, dtype='category')
        assert_frame_equal(result, expected)

    def test_remove_unused_categories(self):
        result = pd.DataFrame(
            {'A': ['a', 'b']},
            # extraneous value
            dtype=pd.api.types.CategoricalDtype(['a', 'b', 'c'])
        )
        sanitize_dataframe(result)
        expected = pd.DataFrame({'A': ['a', 'b']}, dtype='category')
        assert_frame_equal(result, expected)
