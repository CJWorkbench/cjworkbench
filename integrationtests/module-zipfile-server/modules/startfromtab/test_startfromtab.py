from dataclasses import dataclass
from typing import Optional, Dict
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from startfromtab import render


@dataclass(frozen=True)
class RenderColumn:
    """
    Column presented to a render() function in its `input_columns` argument.

    A column has a `name` and a `type`. The `type` is one of "number", "text"
    or "timestamp".
    """

    name: str
    """Column name in the DataFrame."""

    type: str
    """'number', 'text' or 'timestamp'."""

    format: Optional[str]
    """
    Format string for converting the given column to string.

    >>> column = RenderColumn('A', 'number', '{:,d} bottles of beer')
    >>> column.format.format(1234)
    '1,234 bottles of beer'
    """


@dataclass(frozen=True)
class TabOutput:
    """
    Tab data presented to a render() function.

    A tab has `slug` (JS-side ID), `name` (user-assigned tab name), `dataframe`
    (pandas.DataFrame), and `columns` (dict of `RenderColumn`, keyed by each
    column in `dataframe.columns`.)

    `columns` is designed to mirror the `input_columns` argument to render().
    It's a Dict[str, RenderColumn].
    """

    slug: str
    """
    Tab slug (permanent ID, unique in this Workflow, that leaks to the user).
    """

    name: str
    """Tab name visible to the user and editable by the user."""

    columns: Dict[str, RenderColumn]
    """
    Columns output by the final module in this tab.

    `set(columns.keys()) == set(dataframe.columns)`.
    """

    dataframe: pd.DataFrame
    """
    DataFrame output by the final module in this tab.
    """


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
                        "B": RenderColumn("B", "timestamp", None),
                        "C": RenderColumn("C", "text", None),
                    },
                    dataframe,
                )
            },
        )
        assert_frame_equal(result["dataframe"], dataframe)
        self.assertEqual(result["column_formats"], {"A": "{,.2f}"})
