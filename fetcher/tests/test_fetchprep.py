import unittest

from cjwmodule.spec.paramschema import ParamSchema

from cjwkernel.types import Column, ColumnType, TableMetadata
from cjwstate.errors import PromptingError
from fetcher.fetchprep import clean_value


class CleanValueTests(unittest.TestCase):
    def test_clean_float(self):
        result = clean_value(ParamSchema.Float(), 3.0, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_float_with_int_value(self):
        # ParamSchema.Float can have `int` values (because values come from
        # json.parse(), which only gives Numbers so can give "3" instead of
        # "3.0". We want to pass that as `float` in the `params` dict.
        result = clean_value(ParamSchema.Float(), 3, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_file_error(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported: fetch file"):
            clean_value(ParamSchema.File(), None, None)

    def test_clean_normal_dict(self):
        input_shape = TableMetadata(3, [Column("A", ColumnType.Number())])
        schema = ParamSchema.Dict(
            {"str": ParamSchema.String(), "int": ParamSchema.Integer()}
        )
        value = {"str": "foo", "int": 3}
        expected = dict(value)  # no-op
        result = clean_value(schema, value, input_shape)
        self.assertEqual(result, expected)

    def test_clean_column_no_input_is_empty(self):
        self.assertEqual(clean_value(ParamSchema.Column(), "A", TableMetadata()), "")

    def test_clean_column_tab_parameter_is_error(self):
        input_shape = TableMetadata(3, [Column("A", ColumnType.Number())])
        with self.assertRaisesRegex(
            RuntimeError, "Unsupported: fetch column with tab_parameter"
        ):
            clean_value(ParamSchema.Column(tab_parameter="tab-2"), "A", input_shape)

    def test_clean_column_happy_path(self):
        input_shape = TableMetadata(3, [Column("A", ColumnType.Number())])
        self.assertEqual(
            clean_value(
                ParamSchema.Column(column_types=frozenset({"number"})), "A", input_shape
            ),
            "A",
        )

    def test_clean_column_missing(self):
        input_shape = TableMetadata(3, [Column("A", ColumnType.Number())])
        self.assertEqual(clean_value(ParamSchema.Column(), "B", input_shape), "")

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # Consider Regex. We probably want to pass the module a text Series
        # _separately_ from the input DataFrame. That way Regex can output
        # a new Text column but preserve its input column's data type.
        #
        # ... but for now: prompt for a Quick Fix.
        input_shape = TableMetadata(3, [Column("A", ColumnType.Number())])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamSchema.Column(column_types=frozenset({"text"})), "A", input_shape
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], None, frozenset({"text"}))],
        )

    def test_clean_column_prompting_error_convert_to_number(self):
        input_shape = TableMetadata(3, [Column("A", ColumnType.Text())])
        with self.assertRaises(PromptingError) as cm:
            clean_value(
                ParamSchema.Column(column_types=frozenset({"number"})), "A", input_shape
            )

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A"], "text", frozenset({"number"}))],
        )

    def test_dict_prompting_error(self):
        input_shape = TableMetadata(
            3, [Column("A", ColumnType.Text()), Column("B", ColumnType.Text())]
        )
        schema = ParamSchema.Dict(
            {
                "col1": ParamSchema.Column(column_types=frozenset({"number"})),
                "col2": ParamSchema.Column(column_types=frozenset({"timestamp"})),
            }
        )
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {"col1": "A", "col2": "B"}, input_shape)

        self.assertEqual(
            cm.exception.errors,
            [
                PromptingError.WrongColumnType(["A"], "text", frozenset({"number"})),
                PromptingError.WrongColumnType(["B"], "text", frozenset({"timestamp"})),
            ],
        )

    def test_clean_multicolumn_valid(self):
        input_shape = TableMetadata(
            3, [Column("A", ColumnType.Number()), Column("B", ColumnType.Number())]
        )
        result = clean_value(ParamSchema.Multicolumn(), ["A", "B"], input_shape)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multicolumn_no_input_is_empty(self):
        self.assertEqual(
            clean_value(ParamSchema.Multicolumn(), "A", TableMetadata()), []
        )

    def test_clean_multicolumn_sort_in_table_order(self):
        input_shape = TableMetadata(
            3, [Column("B", ColumnType.Number()), Column("A", ColumnType.Number())]
        )
        result = clean_value(ParamSchema.Multicolumn(), ["A", "B"], input_shape)
        self.assertEqual(result, ["B", "A"])

    def test_clean_multicolumn_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # ... but for now: prompt for a Quick Fix.
        input_shape = TableMetadata(
            3,
            [
                Column("A", ColumnType.Number()),
                Column("B", ColumnType.Timestamp()),
                Column("C", ColumnType.Text()),
            ],
        )
        with self.assertRaises(PromptingError) as cm:
            schema = ParamSchema.Multicolumn(column_types=frozenset({"text"}))
            clean_value(schema, "A,B", input_shape)

        self.assertEqual(
            cm.exception.errors,
            [PromptingError.WrongColumnType(["A", "B"], None, frozenset({"text"}))],
        )

    def test_clean_multicolumn_missing_is_removed(self):
        input_shape = TableMetadata(
            3, [Column("A", ColumnType.Number()), Column("B", ColumnType.Number())]
        )
        result = clean_value(ParamSchema.Multicolumn(), ["A", "X", "B"], input_shape)
        self.assertEqual(result, ["A", "B"])

    def test_clean_multichartseries_is_error(self):
        with self.assertRaisesRegex(
            RuntimeError, "Unsupported: fetch multichartseries"
        ):
            clean_value(ParamSchema.Multichartseries(), [], None)

    def test_clean_tab_unsupported(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported: fetch tab"):
            clean_value(ParamSchema.Tab(), "", None)

    def test_clean_multitab_unsupported(self):
        with self.assertRaisesRegex(RuntimeError, "Unsupported: fetch multitab"):
            clean_value(ParamSchema.Multitab(), "", None)
