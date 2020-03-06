import unittest
from staticmodules import pastecsv
from cjwkernel.util import tempfile_context
from cjwkernel.tests.util import assert_arrow_table_equals
from cjwkernel.types import ArrowTable, I18nMessage, RenderError, RenderResult


def P(csv="", has_header_row=True):
    return {"csv": csv, "has_header_row": has_header_row}


def render_arrow(params):
    with tempfile_context(suffix=".arrow") as output_path:
        errors = pastecsv.render(ArrowTable(), params, output_path)
        table = ArrowTable.from_arrow_file_with_inferred_metadata(output_path)
        return RenderResult(table, [RenderError(I18nMessage(*e)) for e in errors])


class PasteCSVTests(unittest.TestCase):
    def test_empty(self):
        result = render_arrow(P(csv="", has_header_row=True))
        assert_arrow_table_equals(result.table, {})
        self.assertEqual(result.errors, [])

    def test_csv(self):
        result = render_arrow(P(csv="A,B\na,b\nc,d"))
        assert_arrow_table_equals(result.table, {"A": ["a", "c"], "B": ["b", "d"]})
        self.assertEqual(result.errors, [])

    def test_tsv(self):
        result = render_arrow(P(csv="A\tB\na\tb\nc\td"))
        assert_arrow_table_equals(result.table, {"A": ["a", "c"], "B": ["b", "d"]})
        self.assertEqual(result.errors, [])

    def test_extra_data_should_not_mangle_index(self):
        # Pandas' default behavior is _really_ weird when the number of values
        # in a row exceeds the number of headers. It tries building a
        # MultiIndex out of the first ones. This is probably so it can read its
        # own string representations? ... but it's terrible for our users.
        result = render_arrow(P(csv="A,B\na,b,c"))
        assert_arrow_table_equals(
            result.table, {"A": ["a"], "B": ["b"], "Column 3": ["c"]}
        )
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "util.colnames.warnings.default",
                        {"n_columns": 1, "first_colname": "Column 3"},
                        "cjwmodule",
                    )
                )
            ],
        )

    def test_list_index_out_of_range(self):
        # Pandas' read_csv() freaks out on even the simplest examples....
        #
        # Today's exhibit:
        # pd.read_csv(io.StringIO('A\n,,'), index_col=False)
        # raises IndexError: list index out of range
        result = render_arrow(P(csv="A\n,,", has_header_row=True))
        assert_arrow_table_equals(
            result.table, {"A": [""], "Column 2": [""], "Column 3": [""]}
        )
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "util.colnames.warnings.default",
                        {"n_columns": 2, "first_colname": "Column 2"},
                        "cjwmodule",
                    )
                )
            ],
        )

    def test_no_header(self):
        result = render_arrow(P(csv="A,B", has_header_row=False))
        assert_arrow_table_equals(result.table, {"Column 1": ["A"], "Column 2": ["B"]})
        self.assertEqual(result.errors, [])

    def test_duplicate_column_names_renamed(self):
        result = render_arrow(P(csv="A,A\na,b", has_header_row=True))
        assert_arrow_table_equals(result.table, {"A": ["a"], "A 2": ["b"]})
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "util.colnames.warnings.numbered",
                        {"n_columns": 1, "first_colname": "A 2"},
                        "cjwmodule",
                    )
                )
            ],
        )

    def test_empty_column_name_gets_automatic_name(self):
        result = render_arrow(P(csv="A,,B\na,b,c", has_header_row=True))
        assert_arrow_table_equals(
            result.table, {"A": ["a"], "Column 2": ["b"], "B": ["c"]}
        )
        self.assertEqual(
            result.errors,
            [
                RenderError(
                    I18nMessage(
                        "util.colnames.warnings.default",
                        {"n_columns": 1, "first_colname": "Column 2"},
                        "cjwmodule",
                    )
                )
            ],
        )

    def test_no_nan(self):
        # https://www.pivotaltracker.com/story/show/163106728
        result = render_arrow(P(csv="A,B\nx,y\nz,NA"))
        assert_arrow_table_equals(result.table, {"A": ["x", "z"], "B": ["y", "NA"]})
        self.assertEqual(result.errors, [])
