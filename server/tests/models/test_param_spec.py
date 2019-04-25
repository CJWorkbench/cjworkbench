import unittest
from server.models.param_dtype import ParamDType as DT
from server.models.param_spec import ParamSpec


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

    def test_list_dtype(self):
        # Check that ParamSpec's with List type produce correct nested DTypes
        param_spec = ParamSpec(
            'p',
            ParamSpec.ParamType.LIST,
            child_parameters = [
                {'id_name': 'intparam', 'type': 'integer', 'name': 'my number'},
                {'id_name': 'colparam', 'type': 'column', 'name': 'my column' }
            ]
        )
        dtype = param_spec.dtype
        expected_dtype = DT.List(
            DT.Dict({
                'intparam' : DT.Integer(),
                'colparam': DT.Column(),
        }))

        # effectively do a deep compare with repr
        self.assertEqual(repr(dtype), repr(expected_dtype))
