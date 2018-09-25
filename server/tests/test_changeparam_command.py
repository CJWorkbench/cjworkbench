from asgiref.sync import async_to_sync
from server.tests.utils import load_and_add_module_from_dict, \
        get_param_by_id_name, DbTestCase
from server.models import ChangeParameterCommand


class ParameterValTests(DbTestCase):
    # Change a value, then undo, redo
    def test_change(self):
        testmodule = {
            'name': 'Parameter Change Test',
            'id_name': 'pchangetest',
            'category': 'tests',
            'parameters': [
                {
                    'name': 'Happy String',
                    'id_name': 'hstring',
                    'type': 'string',
                    'default': 'value 1'
                },
                {
                    'name': 'Happy Number',
                    'id_name': 'hnumber',
                    'type': 'integer',
                    'default': '1'
                },
                {
                    'name': 'Happy Checkbox',
                    'id_name': 'hcheckbox',
                    'type': 'checkbox',
                    'default': True,
                },
            ]
        }
        load_and_add_module_from_dict(testmodule)

        pval = get_param_by_id_name('hstring')
        self.assertEqual(pval.value, 'value 1')
        cmd = async_to_sync(ChangeParameterCommand.create)(pval, 'value 2')
        self.assertEqual(pval.value, 'value 2')
        async_to_sync(cmd.backward)()
        self.assertEqual(pval.value, 'value 1')
        async_to_sync(cmd.forward)()
        self.assertEqual(pval.value, 'value 2')
