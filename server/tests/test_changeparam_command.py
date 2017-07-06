from server.models import ChangeParameterCommand
from django.test import TestCase
from server.tests.utils import *

class ParameterValTests(TestCase):
    def setUp(self):
        testmodule = {
            'name': 'Parameter Change Test',
            'id_name': 'pchangetest',
            'category': 'tests',
            'parameters': [
                {
                  'name': 'Happy String',
                  'id_name' : 'hstring',
                  'type': 'string',
                  'default': 'value 1'
                },
                {
                  'name': 'Happy Number',
                  'id_name' : 'hnumber',
                  'type': 'number',
                  'default': '1'
                },
                {
                  'name': 'Happy Checkbox',
                  'id_name': 'hcheckbox',
                  'type': 'checkbox',
                  'default': True,
                }
              ]
            }
        self.wf_module = load_and_add_module(None, testmodule)

    # Change a value, then undo, redo
    def test_change(self):
        pval = get_param_by_id_name('hstring')
        self.assertEqual(pval.string, 'value 1')
        cmd = ChangeParameterCommand.create(pval, 'value 2')
        self.assertEqual(pval.string, 'value 2')
        cmd.backward()
        self.assertEqual(pval.string, 'value 1')
        cmd.forward()
        self.assertEqual(pval.string, 'value 2')




