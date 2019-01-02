import unittest
from server.models.param_field import ParamDType


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
