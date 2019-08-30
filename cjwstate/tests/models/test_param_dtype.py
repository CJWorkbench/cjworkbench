import unittest
from cjwstate.models.param_spec import ParamDType


DT = ParamDType


class DTypeStringTest(unittest.TestCase):
    def test_coerce_none_to_str(self):
        self.assertEqual(DT.String().coerce(None), "")

    def test_coerce_non_str_to_str(self):
        self.assertEqual(DT.String().coerce({"a": "b"}), "{'a': 'b'}")

    def test_coerce_to_str(self):
        self.assertEqual(DT.String().coerce("blah"), "blah")

    def test_coerce_invalid_unicode(self):
        self.assertEqual(DT.String().coerce("A💩\ud802B"), "A💩\ufffdB")

    def test_coerce_zero_byte(self):
        self.assertEqual(DT.String().coerce("A\x00B"), "A\ufffdB")

    def test_validate_emoji(self):
        DT.String().validate("💩")  # do not raise

    def test_validate_non_str(self):
        with self.assertRaisesRegex(ValueError, "not a string"):
            DT.String().validate(23)

    def test_validate_lone_surrogate(self):
        with self.assertRaisesRegex(ValueError, "surrogates not allowed"):
            DT.String().validate("A\ud802B")

    def test_validate_zero_byte(self):
        with self.assertRaisesRegex(ValueError, "zero byte"):
            DT.String().validate("A\x00B")


class DTypeFloatTest(unittest.TestCase):
    def test_validate_int(self):
        DT.Float().validate(10)  # do not raise


class DTypeFileTest(unittest.TestCase):
    def test_validate_null(self):
        DT.File().validate(None)  # do not raise

    def test_validate_uuid(self):
        DT.File().validate("1e3a5177-ee1a-4832-bfbb-6480b93984ab")  # do not raise

    def test_validate_invalid_str(self):
        with self.assertRaisesRegex(ValueError, "not a UUID string representation"):
            # one character too many
            DT.File().validate("f13aa5177-ee1a-4832-bfbb-6480b93984ab")

    def test_validate_non_str(self):
        with self.assertRaisesRegex(ValueError, "not a string"):
            DT.File().validate(0x13A5177)


class DTypeColumnTest(unittest.TestCase):
    def test_coerce_str_to_column(self):
        self.assertEqual(DT.Column().coerce("blah"), "blah")


class DTypeMulticolumnTest(unittest.TestCase):
    def test_multicolumn_default(self):
        self.assertEqual(DT.Multicolumn().coerce(None), [])

    def test_multicolumn_coerce_list_of_str(self):
        self.assertEqual(DT.Multicolumn().coerce(["x", "y"]), ["x", "y"])

    def test_multicolumn_validate_list_of_str_ok(self):
        DT.Multicolumn().validate(["x", "y"]),

    def test_multicolumn_validate_list_of_non_str_is_error(self):
        with self.assertRaises(ValueError):
            DT.Multicolumn().validate([1, 2])

    def test_multicolumn_validate_str_is_error(self):
        with self.assertRaises(ValueError):
            DT.Multicolumn().validate("X,Y")


class DTypeOptionTest(unittest.TestCase):
    def test_option_validate_inner_ok(self):
        DT.Option(DT.String()).validate("foo")

    def test_option_validate_inner_error(self):
        with self.assertRaises(ValueError):
            DT.Option(DT.String()).validate(3)

    def test_option_coerce_none(self):
        # [2019-06-05] We don't support non-None default on Option params
        self.assertEqual(DT.Option(DT.String(default="x")).coerce(None), None)

    def test_option_coerce_inner(self):
        self.assertEqual(DT.Option(DT.String(default="x")).coerce(3.2), "3.2")


class DTypeMapTest(unittest.TestCase):
    def test_map_validate_ok(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = {"a": "b", "c": "d"}
        dtype.validate(value)

    def test_map_validate_bad_value_dtype(self):
        dtype = ParamDType.Map(value_dtype=ParamDType.String())
        value = {"a": 1, "c": 2}
        with self.assertRaises(ValueError):
            dtype.validate(value)

    def test_map_parse(self):
        dtype = ParamDType.parse(
            {
                "type": "map",
                "value_dtype": {
                    "type": "dict",  # test nesting
                    "properties": {"foo": {"type": "string"}},
                },
            }
        )
        self.assertEqual(
            repr(dtype),
            repr(
                ParamDType.Map(
                    value_dtype=ParamDType.Dict(properties={"foo": ParamDType.String()})
                )
            ),
        )

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
        value = dtype.coerce({"a": 1, "b": None})
        self.assertEqual(value, {"a": "1", "b": ""})
