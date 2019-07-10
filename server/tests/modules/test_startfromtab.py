import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from server.modules.startfromtab import render
from cjworkbench.types import RenderColumn, TabOutput


class StartfromtabTest(unittest.TestCase):
    def test_happy_path(self):
        result = render(
            pd.DataFrame(),
            {
                "tab": TabOutput(
                    "tab-2",
                    "Tab 2",
                    {"A": RenderColumn("A", "number", "{}")},
                    pd.DataFrame({"A": [3, 4]}),
                )
            },
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame({"A": [3, 4]}))
        self.assertEqual(result["column_formats"], {"A": "{}"})

    def test_import_empty_tab(self):
        result = render(
            pd.DataFrame(), {"tab": TabOutput("tab-2", "Tab 2", {}, pd.DataFrame())}
        )
        assert_frame_equal(result["dataframe"], pd.DataFrame())
        self.assertEqual(result["column_formats"], {})

    def test_import_columns_without_formats(self):
        dataframe = pd.DataFrame(
            {
                "A": [1, 2, 3],
                "B": pd.Series(
                    ["2012-01-01", "2015-02-03", "2019-05-23"], dtype="datetime64[ns]"
                ),
                "C": ["a", "b", "c"],
            }
        )

        result = render(
            pd.DataFrame(),
            {
                "tab": TabOutput(
                    "tab-2",
                    "Tab 2",
                    {
                        "A": RenderColumn("A", "number", "{,.2f}"),
                        "B": RenderColumn("B", "datetime", None),
                        "C": RenderColumn("C", "text", None),
                    },
                    dataframe,
                )
            },
        )
        assert_frame_equal(result["dataframe"], dataframe)
        self.assertEqual(result["column_formats"], {"A": "{,.2f}"})
