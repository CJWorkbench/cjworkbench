import asyncio
from pathlib import Path
import unittest
import aiohttp
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjwkernel.pandas.moduleutils import (
    spooled_data_from_url,
    autocast_dtypes_in_place,
)


TestDataPath = Path(__file__).parent.parent / "test_data"


class SpooledDataFromUrlTest(unittest.TestCase):
    def test_relative_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url("/foo"):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            asyncio.run(inner())

    def test_schemaless_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url("//a/b"):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            asyncio.run(inner())

    def test_mailto_url_raises_invalid_url(self):
        async def inner():
            async with spooled_data_from_url("mailto:user@example.org"):
                pass

        with self.assertRaises(aiohttp.InvalidURL):
            asyncio.run(inner())


class AutocastDtypesTest(unittest.TestCase):
    def test_autocast_all_null_is_text(self):
        table = pd.DataFrame({"A": [np.nan, np.nan]}, dtype=object)
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [np.nan, np.nan]}, dtype=object)
        assert_frame_equal(table, expected)

    def test_autocast_all_empty_str_is_text(self):
        table = pd.DataFrame({"A": ["", ""]})
        autocast_dtypes_in_place(table)
        assert_frame_equal(table, pd.DataFrame({"A": ["", ""]}))

    def test_autocast_all_empty_or_null_categories_is_text(self):
        table = pd.DataFrame({"A": ["", np.nan, ""]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": ["", np.nan, ""]}, dtype="category")
        assert_frame_equal(table, expected)

    def test_autocast_int_from_str(self):
        table = pd.DataFrame({"A": ["1", "2"]})
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1, 2]})
        assert_frame_equal(table, expected)

    def test_autocast_int_from_str_categories(self):
        # example: used read_csv(dtype='category'), now want ints
        table = pd.DataFrame({"A": ["1", "2"]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1, 2]})
        assert_frame_equal(table, expected)

    def test_autocast_float_from_str_categories(self):
        # example: used read_csv(dtype='category'), now want floats
        table = pd.DataFrame({"A": ["1", "2.1"]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1.0, 2.1]}, dtype=np.float64)
        assert_frame_equal(table, expected)

    def test_autocast_float_from_str_categories_with_empty_str(self):
        # example: used read_csv(dtype='category'), now want floats
        table = pd.DataFrame({"A": ["1", "2.1", ""]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1.0, 2.1, np.nan]}, dtype=np.float64)
        assert_frame_equal(table, expected)

    def test_autocast_float_from_str_categories_with_dup_floats(self):
        table = pd.DataFrame({"A": ["1", "1.0"]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1.0, 1.0]}, dtype=np.float64)
        assert_frame_equal(table, expected)

    def test_autocast_int_from_str_categories_with_empty_str(self):
        table = pd.DataFrame({"A": ["", "", "1"]}, dtype="category")
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [np.nan, np.nan, 1.0]}, dtype=np.float64)
        assert_frame_equal(table, expected)

    def test_autocast_str_categories_from_str_categories(self):
        table = pd.DataFrame({"A": ["1", "2.1", "Yay"]}, dtype="category")
        autocast_dtypes_in_place(table)  # should be no-op
        expected = pd.DataFrame({"A": ["1", "2.1", "Yay"]}, dtype="category")
        assert_frame_equal(table, expected)

    def test_autocast_mixed_types_to_int(self):
        # This is important in particular for Excel data, which is often a mix
        # of int and str.
        table = pd.DataFrame({"A": ["1", 2]})
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": [1, 2]})
        assert_frame_equal(table, expected)

    def test_autocast_mixed_types_to_str(self):
        # This is important in particular for Excel data, which is often a mix
        # of int and str.
        table = pd.DataFrame({"A": ["1A", 2]})
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": ["1A", "2"]})
        assert_frame_equal(table, expected)

    # We know of no cases in which categories need to be cast to str. If we
    # find some, add the tests here!
    # def test_autocast_mixed_type_categories_to_str()

    def test_autocast_cast_crazy_types(self):
        class Obj:
            def __init__(self, s):
                self.s = s

            def __str__(self):
                return self.s

        obj1 = Obj("o1")
        obj2 = Obj("o2")

        table = pd.DataFrame({"A": [obj1, obj2]})
        autocast_dtypes_in_place(table)
        expected = pd.DataFrame({"A": ["o1", "o2"]})
        assert_frame_equal(table, expected)
