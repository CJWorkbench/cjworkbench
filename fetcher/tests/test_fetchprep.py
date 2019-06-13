from cjworkbench.types import Column, ColumnType, TableShape
from server.models.param_spec import ParamDType
from server.tests.utils import DbTestCase
from fetcher.fetchprep import clean_value
from renderer.execute.types import PromptingError


class CleanValueTests(DbTestCase):
    def test_clean_float(self):
        result = clean_value(ParamDType.Float(), 3.0, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_float_with_int_value(self):
        # ParamDType.Float can have `int` values (because values come from
        # json.parse(), which only gives Numbers so can give "3" instead of
        # "3.0". We want to pass that as `float` in the `params` dict.
        result = clean_value(ParamDType.Float(), 3, None)
        self.assertEqual(result, 3.0)
        self.assertIsInstance(result, float)

    def test_clean_file_error(self):
        with self.assertRaisesRegex(RuntimeError, 'Unsupported: fetch file'):
            clean_value(ParamDType.File(), None, None)

    def test_clean_normal_dict(self):
        input_shape = TableShape(3, [Column('A', ColumnType.NUMBER())])
        schema = ParamDType.Dict({
            'str': ParamDType.String(),
            'int': ParamDType.Integer(),
        })
        value = {'str': 'foo', 'int': 3}
        expected = dict(value)  # no-op
        result = clean_value(schema, value, input_shape)
        self.assertEqual(result, expected)

    def test_clean_column_no_input_is_empty(self):
        self.assertEqual(clean_value(ParamDType.Column(), 'A', None), '')

    def test_clean_column_tab_parameter_is_error(self):
        input_shape = TableShape(3, [Column('A', ColumnType.NUMBER())])
        with self.assertRaisesRegex(
            RuntimeError,
            'Unsupported: fetch column with tab_parameter'
        ):
            clean_value(ParamDType.Column(tab_parameter='tab-2'), 'A',
                        input_shape)

    def test_clean_column_happy_path(self):
        input_shape = TableShape(3, [Column('A', ColumnType.NUMBER())])
        self.assertEqual(
            clean_value(ParamDType.Column(column_types=frozenset({'number'})),
                        'A', input_shape),
            'A'
        )

    def test_clean_column_missing(self):
        input_shape = TableShape(3, [Column('A', ColumnType.NUMBER())])
        self.assertEqual(
            clean_value(ParamDType.Column(), 'B', input_shape),
            ''
        )

    def test_clean_column_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # Consider Regex. We probably want to pass the module a text Series
        # _separately_ from the input DataFrame. That way Regex can output
        # a new Text column but preserve its input column's data type.
        #
        # ... but for now: prompt for a Quick Fix.
        input_shape = TableShape(3, [Column('A', ColumnType.NUMBER())])
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Column(column_types=frozenset({'text'})),
                        'A', input_shape)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'number',
                                           frozenset({'text'})),
        ])

    def test_clean_column_prompting_error_convert_to_number(self):
        input_shape = TableShape(3, [Column('A', ColumnType.TEXT())])
        with self.assertRaises(PromptingError) as cm:
            clean_value(ParamDType.Column(column_types=frozenset({'number'})),
                        'A', input_shape)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
        ])

    def test_dict_prompting_error(self):
        input_shape = TableShape(3, [
            Column('A', ColumnType.TEXT()),
            Column('B', ColumnType.TEXT()),
        ])
        schema = ParamDType.Dict({
            'col1': ParamDType.Column(column_types=frozenset({'number'})),
            'col2': ParamDType.Column(column_types=frozenset({'datetime'})),
        })
        with self.assertRaises(PromptingError) as cm:
            clean_value(schema, {'col1': 'A', 'col2': 'B'}, input_shape)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'text',
                                           frozenset({'number'})),
            PromptingError.WrongColumnType(['B'], 'text',
                                           frozenset({'datetime'})),
        ])

    def test_clean_multicolumn_valid(self):
        input_shape = TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.NUMBER()),
        ])
        result = clean_value(ParamDType.Multicolumn(), ['A', 'B'], input_shape)
        self.assertEqual(result, ['A', 'B'])

    def test_clean_multicolumn_no_input_is_empty(self):
        self.assertEqual(clean_value(ParamDType.Multicolumn(), 'A', None), [])

    def test_clean_multicolumn_sort_in_table_order(self):
        input_shape = TableShape(3, [
            Column('B', ColumnType.NUMBER()),
            Column('A', ColumnType.NUMBER()),
        ])
        result = clean_value(ParamDType.Multicolumn(), ['A', 'B'], input_shape)
        self.assertEqual(result, ['B', 'A'])

    def test_clean_multicolumn_prompting_error_convert_to_text(self):
        # TODO make this _automatic_ instead of quick-fix?
        # ... but for now: prompt for a Quick Fix.
        input_shape = TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.DATETIME()),
            Column('C', ColumnType.TEXT()),
        ])
        with self.assertRaises(PromptingError) as cm:
            schema = ParamDType.Multicolumn(column_types=frozenset({'text'}))
            clean_value(schema, 'A,B', input_shape)

        self.assertEqual(cm.exception.errors, [
            PromptingError.WrongColumnType(['A'], 'number',
                                           frozenset({'text'})),
            PromptingError.WrongColumnType(['B'], 'datetime',
                                           frozenset({'text'})),
        ])

    def test_clean_multicolumn_missing_is_removed(self):
        input_shape = TableShape(3, [
            Column('A', ColumnType.NUMBER()),
            Column('B', ColumnType.NUMBER()),
        ])
        result = clean_value(ParamDType.Multicolumn(), ['A', 'X', 'B'],
                             input_shape)
        self.assertEqual(result, ['A', 'B'])

    def test_clean_multichartseries_is_error(self):
        with self.assertRaisesRegex(RuntimeError,
                                    'Unsupported: fetch multichartseries'):
            clean_value(ParamDType.Multichartseries(), [], None)

    def test_clean_tab_unsupported(self):
        with self.assertRaisesRegex(RuntimeError, 'Unsupported: fetch tab'):
            clean_value(ParamDType.Tab(), '', None)

    def test_clean_multitab_unsupported(self):
        with self.assertRaisesRegex(RuntimeError,
                                    'Unsupported: fetch multitab'):
            clean_value(ParamDType.Multitab(), '', None)
