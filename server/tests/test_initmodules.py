# test module (re)loading
from django.test import TestCase
from server.models import ParameterVal, ParameterSpec, Module, WfModule, Workflow
from server.initmodules import load_module_from_dict
from server.tests.utils import *
import json
import copy

class InitmoduleTests(LoggedInTestCase):
    def setUp(self):
        super(InitmoduleTests, self).setUp()  # log in
        self.loadcsv = {
            'name': 'Load CSV',
            'id_name': 'loadcsv',
            'parameters': [
                {
                  'name': 'URL',
                  'id_name' : 'url',
                  'type': 'string',
                  'default': 'http://foo.com'
                },
                {
                  'name': 'Fetch',
                  'id_name' : 'fetch',
                  'type': 'button',
                  'visible': False
                }
              ]
            }            

        # a new version of LoadCSV that deletes one parameter, changes the type and order of another, and adds a new one
        self.loadcsv2 = {
            'name': 'Load CSV RELOADED',
            'id_name': 'loadcsv',
            'parameters': [
                {
                  'name': 'Retries',
                  'id_name' : 'retries',
                  'type': 'number',
                  'default' : 42
                },
                {
                  'name': 'URL',
                  'id_name': 'url',
                  'type': 'text',
                  'default': 'new url'
                }
              ]
            }

        # create versions of loadcsv that have missing required elements
        self.missing_name = copy.deepcopy(self.loadcsv)
        del self.missing_name['name']

        self.missing_id_name = copy.deepcopy(self.loadcsv)
        del self.missing_id_name['id_name']

        self.missing_param_name = copy.deepcopy(self.loadcsv)
        del self.missing_param_name['parameters'][0]['name']

        self.missing_param_id_name = copy.deepcopy(self.loadcsv)
        del self.missing_param_id_name['parameters'][0]['id_name']

        self.missing_param_type = copy.deepcopy(self.loadcsv)
        del self.missing_param_type['parameters'][0]['type']


    def test_load_valid(self):
        self.assertEqual(len(Module.objects.all()), 0)   # we should be starting with no modules
        load_module_from_dict(self.loadcsv)

        # basic properties
        self.assertEqual(len(Module.objects.all()), 1)
        m = Module.objects.all()[0]
        self.assertEqual(m.name, 'Load CSV')
        self.assertEqual(m.id_name, 'loadcsv')

        # parameters
        pspecs = ParameterSpec.objects.all()
        self.assertEqual(len(pspecs), 2)

        url_spec = ParameterSpec.objects.get(id_name='url')
        self.assertEqual(url_spec.name, 'URL')
        self.assertEqual(url_spec.id_name, 'url')
        self.assertEqual(url_spec.type, ParameterSpec.STRING)
        self.assertEqual(url_spec.def_string, 'http://foo.com')
        self.assertEqual(url_spec.def_visible, True)
        self.assertEqual(url_spec.order, 0)

        button_spec = ParameterSpec.objects.get(id_name='fetch')
        self.assertEqual(button_spec.name, 'Fetch')
        self.assertEqual(button_spec.id_name, 'fetch')
        self.assertEqual(button_spec.type, ParameterSpec.BUTTON)
        self.assertEqual(button_spec.def_visible, False)
        self.assertEqual(button_spec.order, 1)

    # we should bail when keys are missing
    def test_missing_keys(self):
        with self.assertRaises(ValueError):
            load_module_from_dict(self.missing_name)

        with self.assertRaises(ValueError):
            load_module_from_dict(self.missing_id_name)

        with self.assertRaises(ValueError):
            load_module_from_dict(self.missing_param_name)

        with self.assertRaises(ValueError):
            load_module_from_dict(self.missing_param_id_name)

        with self.assertRaises(ValueError):
            load_module_from_dict(self.missing_param_type)


    # checks that a new module with the same id_name overwrites the old, and parameters are fixed up
    def test_module_reload(self):
        self.assertEqual(len(Module.objects.all()), 0)   # we should be starting with no modules
        m1 = load_module_from_dict(self.loadcsv)
        url_spec1 = ParameterSpec.objects.get(id_name='url')
        button_spec1 = ParameterSpec.objects.get(id_name='fetch')

        # create wf_modules in two different workflows that reference this module
        wf1 = add_new_workflow(name='Worky')
        wfm1 = add_new_wf_module(workflow=wf1, module=m1, order=1)
        wfm1.create_default_parameters()
        wf2 = add_new_workflow(name='Worky 2')
        wfm2 = add_new_wf_module(workflow=wf2, module=m1, order=1)
        wfm2.create_default_parameters()

        # precondition: corresponding parameter val exists for each wfm with correct default
        # also tested in test_wfmodule.py but whatevs, won't hurt
        url_pval1 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm1)
        self.assertEqual(url_pval1.string, 'http://foo.com')
        url_pval2 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm2)
        self.assertEqual(url_pval2.string, 'http://foo.com')

        # load the revised module, check that it ends up with the same primary key
        m2 = load_module_from_dict(self.loadcsv2)
        self.assertEqual(m1.id, m2.id)

        # button pspec should be gone
        with self.assertRaises(ParameterSpec.DoesNotExist):
            ParameterSpec.objects.get(id_name='fetch')

        # url spec should still exist with same id, new type, new order
        # existing parameterval should have new default, order
        url_spec2 = ParameterSpec.objects.get(id_name='url')
        self.assertEqual(url_spec1.id, url_spec2.id)
        self.assertEqual(url_spec2.type, ParameterSpec.TEXT)
        self.assertEqual(url_spec2.order, 1)
        url_pval1.refresh_from_db()
        self.assertEqual(url_pval1.string, '')
        self.assertEqual(url_pval1.text, 'new url')
        self.assertEqual(url_pval1.order, 1)
        url_pval2.refresh_from_db()
        self.assertEqual(url_pval2.string, '')
        self.assertEqual(url_pval2.text, 'new url')
        self.assertEqual(url_pval2.order, 1)

        # new Numeric parameter should exist, with corresponding new values in WfModules
        retry_spec = ParameterSpec.objects.get(id_name='retries')
        self.assertEqual(retry_spec.type, ParameterSpec.NUMBER)
        self.assertEqual(retry_spec.def_number, 42)
        self.assertEqual(retry_spec.order, 0)
        retry_pval1 = ParameterVal.objects.get(parameter_spec=retry_spec, wf_module=wfm1)
        self.assertEqual(retry_pval1.number, 42)
        self.assertEqual(retry_pval1.order, 0)
        retry_pval2 = ParameterVal.objects.get(parameter_spec=retry_spec, wf_module=wfm2)
        self.assertEqual(retry_pval2.number, 42)
        self.assertEqual(retry_pval1.order, 0)




