import unittest
from server.models import ParameterSpec


class ParameterSpecTests(unittest.TestCase):
    def test_value_to_str_str(self):
        pspec = ParameterSpec(type=ParameterSpec.STRING)
        self.assertEqual(pspec.value_to_str('blah'), 'blah')

    def test_value_to_str_column(self):
        pspec = ParameterSpec(type=ParameterSpec.COLUMN)
        self.assertEqual(pspec.value_to_str('blah'), 'blah')

    def test_value_to_str_multicolumn(self):
        pspec = ParameterSpec(type=ParameterSpec.MULTICOLUMN)
        self.assertEqual(pspec.value_to_str('blah,beep'), 'blah,beep')

    def test_value_to_str_custom(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.value_to_str('{"A":"B"}'), '{"A":"B"}')

    def test_value_to_str_button(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.value_to_str('Create'), 'Create')

    def test_value_to_str_statictext(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.value_to_str('Hello'), 'Hello')

    def test_value_to_str_int(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.value_to_str(1), '1')

    def test_value_to_str_int_from_str(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.value_to_str('1'), '1')

    def test_value_to_str_int_from_invalid_str(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.value_to_str('hi'), '0')

    def test_value_to_str_int_from_empty(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.value_to_str(''), '0')

    def test_value_to_str_int_from_none(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.value_to_str(None), '0')

    def test_value_to_str_float(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.value_to_str(1.1), '1.1')

    def test_value_to_str_float_from_str(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.value_to_str('1.1'), '1.1')

    def test_value_to_str_float_from_invalid_str(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.value_to_str('hi'), '0.0')

    def test_value_to_str_float_from_empty(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.value_to_str(''), '0.0')

    def test_value_to_str_float_from_none(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.value_to_str(None), '0.0')

    def test_value_to_str_checkbox(self):
        pspec = ParameterSpec(type=ParameterSpec.CHECKBOX)
        self.assertEqual(pspec.value_to_str(True), 'True')
        self.assertEqual(pspec.value_to_str(False), 'False')

    def test_value_to_str_checkbox_from_str(self):
        pspec = ParameterSpec(type=ParameterSpec.CHECKBOX)
        self.assertEqual(pspec.value_to_str('true'), 'True')
        self.assertEqual(pspec.value_to_str('false'), 'False')

    def test_value_to_str_checkbox_from_empty_str(self):
        pspec = ParameterSpec(type=ParameterSpec.CHECKBOX)
        self.assertEqual(pspec.value_to_str(''), 'False')

    def test_value_to_str_checkbox_from_none(self):
        pspec = ParameterSpec(type=ParameterSpec.CHECKBOX)
        self.assertEqual(pspec.value_to_str(None), 'False')

    def test_value_to_str_secret(self):
        pspec = ParameterSpec(type=ParameterSpec.SECRET)
        self.assertEqual(
            pspec.value_to_str({'name': 'foo', 'secret': 'bar'}),
            '{"name": "foo", "secret": "bar"}'
        )

    def test_value_to_str_secret_no_name_raises(self):
        pspec = ParameterSpec(type=ParameterSpec.SECRET)

        with self.assertRaises(ValueError):
            pspec.value_to_str({'namex': 'foo', 'secret': 'bar'})

        with self.assertRaises(ValueError):
            pspec.value_to_str({'name': '', 'secret': 'bar'})

    def test_value_to_str_secret_no_secret_raises(self):
        pspec = ParameterSpec(type=ParameterSpec.SECRET)

        with self.assertRaises(ValueError):
            pspec.value_to_str({'name': 'foo', 'secretx': 'bar'})

        with self.assertRaises(ValueError):
            pspec.value_to_str({'name': 'foo', 'secret': ''})

    def test_value_to_str_invalid_type(self):
        pspec = ParameterSpec(type='invalid')
        with self.assertRaises(ValueError):
            pspec.value_to_str('hi')

    def test_str_to_value_str(self):
        pspec = ParameterSpec(type=ParameterSpec.STRING)
        self.assertEqual(pspec.str_to_value('blah'), 'blah')

    def test_str_to_value_column(self):
        pspec = ParameterSpec(type=ParameterSpec.COLUMN)
        self.assertEqual(pspec.str_to_value('blah'), 'blah')

    def test_str_to_value_multicolumn(self):
        pspec = ParameterSpec(type=ParameterSpec.MULTICOLUMN)
        self.assertEqual(pspec.str_to_value('blah,beep'), 'blah,beep')

    def test_str_to_value_custom(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.str_to_value('{"A":"B"}'), '{"A":"B"}')

    def test_str_to_value_button(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.str_to_value('Create'), 'Create')

    def test_str_to_value_statictext(self):
        pspec = ParameterSpec(type=ParameterSpec.CUSTOM)
        self.assertEqual(pspec.str_to_value('Hello'), 'Hello')

    def test_str_to_value_int(self):
        pspec = ParameterSpec(type=ParameterSpec.INTEGER)
        self.assertEqual(pspec.str_to_value('1'), 1)

    def test_str_to_value_float(self):
        pspec = ParameterSpec(type=ParameterSpec.FLOAT)
        self.assertEqual(pspec.str_to_value('1.1'), 1.1)

    def test_str_to_value_checkbox(self):
        pspec = ParameterSpec(type=ParameterSpec.CHECKBOX)
        self.assertEqual(pspec.str_to_value('True'), True)
        self.assertEqual(pspec.str_to_value('False'), False)

    def test_str_to_value_secret_hides_secret(self):
        pspec = ParameterSpec(type=ParameterSpec.SECRET)
        self.assertEqual(
            pspec.str_to_value('{"name": "foo", "secret": "bar"}'),
            {'name': 'foo'}
        )

    def test_str_to_value_secret_empty(self):
        pspec = ParameterSpec(type=ParameterSpec.SECRET)
        self.assertEqual(pspec.str_to_value(''), None)

    def test_str_to_value_invalid_type(self):
        pspec = ParameterSpec(type='invalid')
        with self.assertRaises(ValueError):
            pspec.str_to_value('hi')
