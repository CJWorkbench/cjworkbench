import unittest
from server.models.param_spec import ParamDType, ParamSpec


DT = ParamDType


class DTypeCoerceTest(unittest.TestCase):
    def test_coerce_str_to_str(self):
        self.assertEqual(DT.String().coerce('blah'), 'blah')

    def test_coerce_none_to_str(self):
        self.assertEqual(DT.String().coerce(None), '')

    def test_coerce_non_str_to_str(self):
        self.assertEqual(DT.String().coerce({'a': 'b'}), "{'a': 'b'}")

    def test_coerce_str_to_column(self):
        self.assertEqual(DT.Column().coerce('blah'), 'blah')

    def test_coerce_str_to_multicolumn(self):
        self.assertEqual(DT.Multicolumn().coerce('blah,beep'), 'blah,beep')

    def test_map_validate_ok(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = {'a': 'b', 'c': 'd'}
        dtype.validate(value)

    def test_map_validate_bad_value_dtype(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = {'a': 1, 'c': 2}
        with self.assertRaises(ValueError):
            dtype.validate(value)

    def test_map_parse(self):
        dtype = ParamDType.parse({
            'type': 'map',
            'value_dtype': {
                'type': 'dict',  # test nesting
                'properties': {
                    'foo': {'type': 'string'},
                },
            },
        })
        self.assertEqual(repr(dtype), repr(ParamDType.Map(
            value_dtype=ParamDType.Dict(properties={
                'foo': ParamDType.String(),
            })
        )))

    def test_map_coerce_none(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = dtype.coerce(None)
        self.assertEqual(value, {})

    def test_map_coerce_non_dict(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = dtype.coerce([1, 2, 3])
        self.assertEqual(value, {})

    def test_map_coerce_dict_wrong_value_type(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = dtype.coerce({'a': 1, 'b': None})
        self.assertEqual(value, {'a': '1', 'b': ''})

    def test_map_omit_missing_table_columns(self):
        # Currently, "omit" means "set empty". There's a valid use case for
        # actually _removing_ colnames here, but [adamhooper, 2019-01-04] we
        # haven't defined that case yet.
        dtype = ParamDType.Map(value_dtype=ParamDType.Column())
        value = dtype.omit_missing_table_columns({'a': 'X', 'b': 'Y'}, {'X'})
        self.assertEqual(value, {'a': 'X', 'b': ''})

    def test_multichartseries_omit_missing_table_columns(self):
        dtype = ParamDType.Multichartseries()
        value = dtype.omit_missing_table_columns([
            {'column': 'X', 'color': '#abcdef'},
            {'column': 'Y', 'color': '#abc123'},
        ], {'X', 'Z'})
        self.assertEqual(value, [{'column': 'X', 'color': '#abcdef'}])


class ParamSpecDTypeTest(unittest.TestCase):
    def test_bool_radio_default_false(self):
        # Handle odd edge case seen on production:
        #
        # If enum options are booleans and the first is True, and the _default_
        # is False, don't overwrite the default.
        param_spec = ParamSpec(
            'p',
            ParamSpec.ParamType.RADIO,
            options=[
                {'value': True, 'label': 'First'},
                {'value': False, 'label': 'Second'},
            ],
            default=False  # a valid option
        )
        dtype = param_spec.dtype
        self.assertEqual(dtype.default, False)
