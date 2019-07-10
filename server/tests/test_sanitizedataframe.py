import json
import os
from unittest import TestCase
from django.conf import settings
import numpy as np
import pandas as pd
from pandas.util import hash_pandas_object
from pandas.testing import assert_series_equal
from server.sanitizedataframe import sanitize_series


class SanitizeDataFrameTest(TestCase):
    def test_mixed_to_string_keeps_nan(self):
        # check that sanitizing a non-string column with missing data produces
        # empty cells, not 'nan' strings
        # https://www.pivotaltracker.com/story/show/154619564
        series = pd.Series([1.0, "str", np.nan, ""])  # mixed
        result = sanitize_series(series)
        assert_series_equal(result, pd.Series(["1.0", "str", np.nan, ""]))

    def test_mixed_to_string_allows_custom_types(self):
        class Obj:
            def __str__(self):
                return "x"

        series = pd.Series([Obj(), Obj()])
        result = sanitize_series(series)
        expected = pd.Series(["x", "x"])
        assert_series_equal(result, expected)

    def test_categories_to_string_allows_custom_category_types(self):
        class Obj:
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        series = pd.Series([Obj("a"), Obj("b"), Obj("a"), "a", "y"], dtype="category")
        result = sanitize_series(series)
        expected = pd.Series(["a", "b", "a", "a", "y"], dtype="category")
        assert_series_equal(result, expected)

    def test_categories_to_string_allows_abnormal_index(self):
        class Obj:
            def __init__(self, value):
                self.value = value

            def __str__(self):
                return self.value

        # Slicing a Series means the category list remains complete, even
        # though some categories aren't used. In this example, `series` has an
        # Obj('a') category, even though the value doesn't appear anywhere in
        # the dataframe. (This is because slicing creates a numpy "view", not a
        # copy of the original array of codes.)
        #
        # Sanitize's output shouldn't include any categories that aren't
        # visible. (The data in memory should not be a "view".)
        #
        # Also, sanitize_series() should reset the index.
        series = pd.Series([Obj("a"), Obj("b"), "c", "b"], dtype="category")[1:]
        result = sanitize_series(series)
        expected = pd.Series(["b", "c", "b"], dtype="category")
        assert_series_equal(result, expected)
        # to reiterate: 'result' has no category that looks like 'a'.
        self.assertEqual(sorted(result.cat.categories.tolist()), ["b", "c"])

    def test_lists_and_dicts(self):
        series = pd.Series([[5, 6, 7], {"a": "b"}])
        result = sanitize_series(series)
        expected = pd.Series(["[5, 6, 7]", "{'a': 'b'}"])
        assert_series_equal(result, expected)

    def test_reset_index(self):
        # should always come out with row numbers contiguous from zero
        series = pd.Series([1, 2, 3])[1:]
        result = sanitize_series(series)
        assert_series_equal(result, pd.Series([2, 3]))  # index is [0,1]

    def test_cast_int_category_to_int(self):
        series = pd.Series([1, 2], dtype="category")
        result = sanitize_series(series)
        assert_series_equal(result, pd.Series([1, 2]))

    def test_cast_mixed_category_to_str(self):
        series = pd.Series([1, "2"], dtype="category")
        result = sanitize_series(series)
        expected = pd.Series(["1", "2"], dtype="category")
        assert_series_equal(result, expected)

    def test_remove_unused_categories(self):
        series = pd.Series(
            ["a", "b"],
            # extraneous value
            dtype=pd.api.types.CategoricalDtype(["a", "b", "c"]),
        )
        result = sanitize_series(series)
        expected = pd.Series(["a", "b"], dtype="category")
        assert_series_equal(result, expected)
