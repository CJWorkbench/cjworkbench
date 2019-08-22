import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.pandas_util import validate_dataframe


class ValidateDataframeTest(unittest.TestCase):
    def test_index(self):
        with self.assertRaisesRegex(ValueError, "must use the default RangeIndex"):
            validate_dataframe(pd.DataFrame({"A": [1, 2]})[1:])

    def test_non_str_objects(self):
        with self.assertRaisesRegex(ValueError, "must all be str"):
            validate_dataframe(pd.DataFrame({"foo": ["a", 1]}))

    def test_empty_categories_with_wrong_dtype(self):
        with self.assertRaisesRegex(ValueError, "must have dtype=object"):
            validate_dataframe(
                pd.DataFrame({"foo": [np.nan]}, dtype=float).astype("category")
            )

    def test_non_str_categories(self):
        with self.assertRaisesRegex(ValueError, "must all be str"):
            validate_dataframe(pd.DataFrame({"foo": ["a", 1]}, dtype="category"))

    def test_unused_categories(self):
        with self.assertRaisesRegex(ValueError, "unused category 'b'"):
            validate_dataframe(
                pd.DataFrame({"foo": ["a", "a"]}, dtype=pd.CategoricalDtype(["a", "b"]))
            )

    def test_null_is_not_a_category(self):
        # pd.CategoricalDtype means storing nulls as -1. Don't consider -1 when
        # counting the used categories.
        with self.assertRaisesRegex(ValueError, "unused category 'b'"):
            validate_dataframe(
                pd.DataFrame(
                    {"foo": ["a", None]}, dtype=pd.CategoricalDtype(["a", "b"])
                )
            )

    def test_empty_categories(self):
        df = pd.DataFrame({"A": []}, dtype="category")
        validate_dataframe(df)

    def test_unique_colnames(self):
        dataframe = pd.DataFrame({"A": [1], "B": [2]})
        dataframe.columns = ["A", "A"]
        with self.assertRaisesRegex(ValueError, "duplicate column name"):
            validate_dataframe(dataframe)

    def test_empty_colname(self):
        dataframe = pd.DataFrame({"": [1], "B": [2]})
        with self.assertRaisesRegex(ValueError, "empty column name"):
            validate_dataframe(dataframe)

    def test_numpy_dtype(self):
        # Numpy dtypes should be treated just like pandas dtypes.
        dataframe = pd.DataFrame({"A": np.array([1, 2, 3])})
        validate_dataframe(dataframe)

    def test_unsupported_dtype(self):
        dataframe = pd.DataFrame(
            {
                # A type we never plan on supporting
                "A": pd.Series([pd.Interval(0, 1)], dtype="interval")
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            validate_dataframe(dataframe)

    def test_datetime64tz_unsupported(self):
        dataframe = pd.DataFrame(
            {
                # We don't support datetimes with time zone data ... yet
                "A": pd.Series([pd.to_datetime("2019-04-23T12:34:00-0500")])
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            validate_dataframe(dataframe)

    def test_nullable_int_unsupported(self):
        dataframe = pd.DataFrame(
            {
                # We don't support nullable integer columns ... yet
                "A": pd.Series([1, np.nan], dtype=pd.Int64Dtype())
            }
        )
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            validate_dataframe(dataframe)

    def test_infinity_not_supported(self):
        # Make 'A': [1, -inf, +inf, nan]
        num = pd.Series([1, -2, 3, np.nan])
        denom = pd.Series([1, 0, 0, 1])
        dataframe = pd.DataFrame({"A": num / denom})
        with self.assertRaisesRegex(
            ValueError,
            (
                "invalid value -inf in column 'A', row 1 "
                "\(infinity is not supported\)"
            ),
        ):
            validate_dataframe(dataframe)

    def test_unsupported_numpy_dtype_unsupported(self):
        # We can't check if a numpy dtype == 'category'.
        # https://github.com/pandas-dev/pandas/issues/16697
        arr = np.array([1, 2, 3]).astype("complex")  # we don't support complex
        dataframe = pd.DataFrame({"A": arr})
        with self.assertRaisesRegex(ValueError, "unsupported dtype"):
            validate_dataframe(dataframe)

    def test_colnames_dtype_object(self):
        with self.assertRaisesRegex(ValueError, "column names"):
            # df.columns is numeric
            validate_dataframe(pd.DataFrame({1: [1]}))

    def test_colnames_all_str(self):
        with self.assertRaisesRegex(ValueError, "column names"):
            # df.columns is object, but not all are str
            validate_dataframe(pd.DataFrame({"A": [1], 2: [2]}))
