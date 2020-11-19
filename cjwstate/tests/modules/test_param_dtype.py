import unittest
from cjwstate.modules.param_dtype import ParamDType


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

    def test_column_parse_column_types_as_frozenset(self):
        self.assertEqual(
            DT.Column._from_plain_data(column_types=["timestamp", "number"]),
            DT.Column(column_types=frozenset(["timestamp", "number"])),
        )


class DTypeTimezoneTest(unittest.TestCase):
    def test_coerce_str_to_timezone(self):
        self.assertEqual(DT.Timezone().coerce("America/Montreal"), "America/Montreal")

    def test_coerce_nonsense_str_to_utc(self):
        self.assertEqual(DT.Timezone().coerce("America/NotMontreal"), "UTC")

    def test_validate_ok(self):
        DT.Timezone().validate("America/Montreal")  # no error

    def test_validate_value_error(self):
        with self.assertRaises(ValueError):
            DT.Timezone().validate("America/NotMontreal")

    def test_parse(self):
        self.assertEqual(
            DT.Timezone._from_plain_data(default="America/Montreal"),
            DT.Timezone(default="America/Montreal"),
        )


class DTypeMulticolumnTest(unittest.TestCase):
    def test_multicolumn_default(self):
        self.assertEqual(DT.Multicolumn().coerce(None), [])

    def test_multicolumn_parse_column_types_as_frozenset(self):
        self.assertEqual(
            DT.Multicolumn._from_plain_data(column_types=["timestamp", "number"]),
            DT.Multicolumn(column_types=frozenset(["timestamp", "number"])),
        )

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


class DTypeConditionTest(unittest.TestCase):
    def test_coerce_none(self):
        self.assertEqual(
            DT.Condition().coerce(None), {"operation": "and", "conditions": []}
        )

    def test_coerce_valid(self):
        value = {
            "operation": "and",
            "conditions": [
                {
                    "operation": "or",
                    "conditions": [
                        {
                            "operation": "text_is",
                            "column": "A",
                            "value": "foo",
                            "isCaseSensitive": True,
                            "isRegex": False,
                        }
                    ],
                }
            ],
        }
        self.assertEqual(DT.Condition().coerce(value), value)

    def test_coerce_invalid(self):
        value = {"operation": "blargh", "subparams": {"foo": "bar"}}
        self.assertEqual(
            DT.Condition().coerce(value), {"operation": "and", "conditions": []}
        )

    def test_validate_missing_conditions(self):
        with self.assertRaises(ValueError):
            DT.Condition().validate({"operation": "and", "condition": []})

    def test_validate_conditions_not_list(self):
        with self.assertRaises(ValueError):
            DT.Condition().validate({"operation": "and", "conditions": "hi"})

    def test_validate_and_with_extra_property(self):
        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {"operation": "and", "conditions": [], "foo": "bar"}
            )

    def test_validate_not_2_levels(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        # level 0
        with self.assertRaises(ValueError):
            DT.Condition().validate(comparison)

        # level 1
        with self.assertRaises(ValueError):
            DT.Condition().validate({"operation": "and", "conditions": [comparison]})

        # level 2 is okay
        DT.Condition().validate(
            {
                "operation": "and",
                "conditions": [{"operation": "or", "conditions": [comparison]}],
            }
        )

        # level 3
        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [
                        {
                            "operation": "or",
                            "conditions": [
                                {"operation": "and", "conditions": [comparison]}
                            ],
                        }
                    ],
                }
            )

    def test_validate_no_such_operation(self):
        comparison = {
            "operation": "text_is_blargy",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_empty_operation_is_okay(self):
        # The UI lets users select nothing. We can't stop them.
        comparison = {
            "operation": "",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": False,
        }

        DT.Condition().validate(
            {
                "operation": "and",
                "conditions": [{"operation": "or", "conditions": [comparison]}],
            }
        )

    def test_validate_missing_key(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
        }

        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_extra_key(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": "x",
            "isCaseSensitive": True,
            "isRegex": True,
            "isSomethingElse": False,
        }

        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )

    def test_validate_condition_value_wrong_type(self):
        comparison = {
            "operation": "text_is",
            "column": "A",
            "value": 312,
            "isCaseSensitive": True,
            "isRegex": False,
        }

        with self.assertRaises(ValueError):
            DT.Condition().validate(
                {
                    "operation": "and",
                    "conditions": [{"operation": "or", "conditions": [comparison]}],
                }
            )
