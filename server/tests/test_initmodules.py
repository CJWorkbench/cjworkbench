# test module (re)loading
from django.test import TestCase
from server.models import ParameterVal, ParameterSpec, Module, WfModule, Workflow
from server.initmodules import load_module_from_dict, update_wfm_parameters_to_new_version
from server.tests.utils import *
import json
import copy
from cjworkbench.settings import KB_ROOT_URL

class InitmoduleTests(LoggedInTestCase):
    def setUp(self):
        super(InitmoduleTests, self).setUp()  # log in
        self.loadcsv = {
            'name': 'Load CSV',
            'id_name': 'loadcsv',
            'category': 'Sources',
            'help_url': 'http://help.com/help',
            'parameters': [
                {
                    'name': 'URL',
                    'id_name' : 'url',
                    'type': 'string',
                    'default': 'http://foo.com'
                },
                {
                    'name': 'Name',
                    'id_name': 'name',
                    'type': 'string',
                    'placeholder': 'Type in a name and hit enter'
                },
                {
                    'name': 'Fetch',
                    'id_name' : 'fetch',
                    'type': 'button',
                    'visible': False,
                    'ui-only': True
                },
                {
                    'name': 'No default',
                    'id_name': 'nodefault',
                    'type': 'string',
                    'multiline': True,
                    'derived-data' : True
                },
                {
                    'name': 'Do it checkbox',
                    'id_name': 'doitcheckbox',
                    'type': 'checkbox',
                    'default': True
                }
            ]
        }

        # a new version of LoadCSV that deletes one parameter, changes the type and order of another,
        # and adds a new one, and tests menu param
        self.loadcsv2 = {
            'name': 'Load CSV RELOADED',
            'id_name': 'loadcsv',
            'category' : 'Sources',
            'parameters': [
                {
                  'name': 'Cake type',
                  'id_name' : 'caketype',
                  'type': 'menu',
                  'menu_items' : 'Cheese|Chocolate',
                  'default' : 1
                },
                {
                  'name': 'URL',
                  'id_name': 'url',
                  'type': 'integer',
                  'default': '42'
                }
              ]
            }


    def test_load_valid(self):
        self.assertEqual(len(Module.objects.all()), 0)   # we should be starting with no modules
        load_module_from_dict(self.loadcsv)

        # basic properties
        self.assertEqual(len(Module.objects.all()), 1)
        m = Module.objects.all()[0]
        self.assertEqual(m.name, 'Load CSV')
        self.assertEqual(m.id_name, 'loadcsv')
        self.assertEqual(m.help_url, 'http://help.com/help')

        # parameters
        pspecs = ParameterSpec.objects.all()
        self.assertEqual(len(pspecs), 5)

        url_spec = ParameterSpec.objects.get(id_name='url')
        self.assertEqual(url_spec.name, 'URL')
        self.assertEqual(url_spec.id_name, 'url')
        self.assertEqual(url_spec.type, ParameterSpec.STRING)
        self.assertEqual(url_spec.def_value, 'http://foo.com')
        self.assertEqual(url_spec.def_visible, True)
        self.assertEqual(url_spec.ui_only, False)
        self.assertEqual(url_spec.multiline, False)
        self.assertEqual(url_spec.derived_data, False)
        self.assertEqual(url_spec.order, 0)

        name = ParameterSpec.objects.get(id_name='name')
        self.assertEqual(name.name, 'Name')
        self.assertEqual(name.id_name, 'name')
        self.assertEqual(name.type, ParameterSpec.STRING)
        self.assertEqual(name.placeholder, 'Type in a name and hit enter')

        button_spec = ParameterSpec.objects.get(id_name='fetch')
        self.assertEqual(button_spec.name, 'Fetch')
        self.assertEqual(button_spec.id_name, 'fetch')
        self.assertEqual(button_spec.type, ParameterSpec.BUTTON)
        self.assertEqual(button_spec.def_visible, False)
        self.assertEqual(button_spec.ui_only, True)
        self.assertEqual(button_spec.order, 2)

        # check missing default has a default, and that multiline works
        nodef_spec = ParameterSpec.objects.get(id_name='nodefault')
        self.assertEqual(nodef_spec.type, ParameterSpec.STRING)
        self.assertEqual(nodef_spec.def_value, '')
        self.assertEqual(nodef_spec.multiline, True)
        self.assertEqual(nodef_spec.derived_data, True)

        # Make sure checkbox loads with correct default value
        # This tests boolean -> string conversion (JSON is boolean, def_value is string)
        cb_spec = ParameterSpec.objects.get(id_name='doitcheckbox')
        self.assertEqual(cb_spec.type, ParameterSpec.CHECKBOX)
        self.assertEqual(cb_spec.def_value, 'True')


    # we should bail when keys are missing
    def test_missing_keys(self):
        module_keys = ['name','id_name','category']
        for k in module_keys:
            missing = copy.deepcopy(self.loadcsv)
            del missing[k]
            with self.assertRaises(ValueError):
                load_module_from_dict(missing)

        param_keys = ['name','id_name','type']
        for k in param_keys:
            missing = copy.deepcopy(self.loadcsv)
            del missing['parameters'][0][k]
            with self.assertRaises(ValueError):
                load_module_from_dict(missing)


    # Reloading an external module should create a new module_version, but not add new parameters
    def test_reload_external_module(self):
        # source_version => external
        mini_module = {
            'name': 'Test',
            'id_name': 'test',
            'category': 'Cats',
            'source_version' : 'f00dbeef',
            'parameters': [
                {
                    'name': 'URL',
                    'id_name': 'url',
                    'type': 'string',
                },
            ]
        }

        m1 = load_module_from_dict(mini_module)
        self.assertEqual(m1.source_version_hash, mini_module['source_version'])
        pspec1 = ParameterSpec.objects.get(id_name='url', module_version=m1)

        # Create a wf_module that references this module. Should create a new ParameterVal
        wf = add_new_workflow(name='Worky')
        wfm = add_new_wf_module(workflow=wf, module_version=m1, order=1)
        ParameterVal.objects.get(parameter_spec=pspec1)

        mini_module2 = {
            'name': 'Test',
            'id_name': 'test',
            'category': 'Cats',
            'source_version' : 'deadbeef',
            'parameters': [
                {
                    'name': 'URL',
                    'id_name': 'url',
                    'type': 'string',
                },
                {
                    'name': 'New Integer',
                    'id_name': 'newint',
                    'type' : 'integer'
                }
            ]
        }

        # loading new definition should create new module_version, should not add/alter old parameter values
        m2 = load_module_from_dict(mini_module2)
        self.assertNotEqual(m1.id, m2.id)
        with self.assertRaises(ParameterVal.DoesNotExist):
            ParameterVal.objects.get(parameter_spec__id_name='newint')

        # load same version again, should re-use module_version
        m3 = load_module_from_dict(mini_module2)
        self.assertEqual(m2.id, m3.id)

        # load a different version
        mini_module4 = copy.deepcopy(mini_module2)
        mini_module4['source_version'] = 'f0f0beef'
        m4 = load_module_from_dict(mini_module4)
        self.assertNotEqual(m3.id, m4.id)


    # Checks that re-importing an internal module (same id_name) overwrites the old fields
    # and existing ParameterVals are updated
    def test_reload_internal_module(self):
        self.assertEqual(len(Module.objects.all()), 0)   # we should be starting with no modules

        m1 = load_module_from_dict(self.loadcsv)
        url_spec1 = ParameterSpec.objects.get(id_name='url')
        ParameterSpec.objects.get(id_name='fetch')
        self.assertEqual(m1.source_version_hash, '1.0')  # internal modules get this version

        # create wf_modules in two different workflows that reference this module
        wf1 = add_new_workflow(name='Worky')
        wfm1 = add_new_wf_module(workflow=wf1, module_version=m1, order=1)
        wf2 = add_new_workflow(name='Worky 2')
        wfm2 = add_new_wf_module(workflow=wf2, module_version=m1, order=1)

        # precondition: corresponding parameter val exists for each wfm with correct default
        # also tested in test_wfmodule.py but whatevs, won't hurt
        url_pval1 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm1)
        self.assertEqual(url_pval1.value, 'http://foo.com')
        url_pval2 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm2)
        self.assertEqual(url_pval2.value, 'http://foo.com')

        # load the revised module, check that it ends up with the same primary key
        m2 = load_module_from_dict(self.loadcsv2)
        self.assertEqual(m1.id, m2.id)
        self.assertEqual(m2.module.help_url, '')

        # button pspec should be gone
        with self.assertRaises(ParameterSpec.DoesNotExist):
            ParameterSpec.objects.get(id_name='fetch')

        # parametervals should now point to spec with new type, order, default value
        # and have value=default value because type changed
        self.assertEqual(ParameterSpec.objects.filter(id_name='url').count(), 1)
        url_spec2 = ParameterSpec.objects.get(id_name='url')
        self.assertEqual(url_spec2.type, ParameterSpec.INTEGER)
        self.assertEqual(url_spec2.order, 1)
        self.assertEqual(url_spec2.def_value, '42')
        url_pval1.refresh_from_db()
        self.assertEqual(url_pval1.value, '42')
        self.assertEqual(url_pval1.parameter_spec.id, url_spec2.id)
        url_pval2.refresh_from_db()
        self.assertEqual(url_pval2.value, '42')
        self.assertEqual(url_pval2.parameter_spec.id, url_spec2.id)

        # new Menu parameter should exist, with corresponding new values in WfModules
        menu_spec = ParameterSpec.objects.get(id_name='caketype')
        self.assertEqual(menu_spec.type, ParameterSpec.MENU)
        self.assertEqual(menu_spec.def_value, '1')
        self.assertEqual(menu_spec.def_menu_items, 'Cheese|Chocolate')
        self.assertEqual(menu_spec.order, 0)
        menu_pval1 = ParameterVal.objects.get(parameter_spec=menu_spec, wf_module=wfm1)
        self.assertEqual(menu_pval1.value, '1')
        self.assertEqual(menu_pval1.order, 0)
        menu_pval2 = ParameterVal.objects.get(parameter_spec=menu_spec, wf_module=wfm2)
        self.assertEqual(menu_pval2.value, '1')
        self.assertEqual(menu_pval1.order, 0)

        # load the old one again, just for kicks (and to test updating a previously updated module_version)
        m2 = load_module_from_dict(self.loadcsv)


    # A brief check of conditional UI, in that the JSON can be stored and retrieved correctly.
    def test_condui(self):
        # A very barebones module to test conditional UI loading
        cond_ui_valid = {
            'name': 'CondUI1',
            'id_name': 'condui1',
            'category': 'Analyze',
            'parameters': [
                {
                    'name': 'cond_menu',
                    'id_name': 'cond_menu',
                    'type': 'menu',
                    'menu_items': 'cond1|cond2|cond3'
                },
                {
                    'name': 'cond_test',
                    'id_name': 'cond_test',
                    'type': 'checkbox',
                    'visible_if': {
                        'id_name': 'cond_menu',
                        'value': 'cond1|cond3'
                    }
                }
            ]
        }

        self.assertEqual(len(Module.objects.all()), 0)
        load_module_from_dict(cond_ui_valid)
        cond_spec = ParameterSpec.objects.get(id_name='cond_test')
        cond_spec_visibility = json.loads(cond_spec.visible_if)
        self.assertEqual(cond_spec_visibility, cond_ui_valid['parameters'][1]['visible_if'])

        new_cond_ui = copy.copy(cond_ui_valid)
        del new_cond_ui['parameters'][1]['visible_if']['value']
        with self.assertRaises(ValueError):
            load_module_from_dict(new_cond_ui) # this also tests that db is still valid if load fails

        new_cond_ui['parameters'][1]['visible_if']['value'] = 'cond1|cond2'
        load_module_from_dict(new_cond_ui)
        cond_spec_new = ParameterSpec.objects.get(id_name='cond_test')
        cond_spec_visibility_new = json.loads(cond_spec_new.visible_if)
        self.assertEqual(cond_spec_visibility_new, new_cond_ui['parameters'][1]['visible_if'])


    def test_update_module_to_new_spec(self):
        # Setup a workflow, wfmodule, and parameter vals
        module = Module.objects.create()
        module_version1 = ModuleVersion.objects.create(module=module)
        unchanged_spec = ParameterSpec.objects.create(id_name='unchanged', type='string', module_version=module_version1)
        changed_spec = ParameterSpec.objects.create(id_name='changed', type='string', module_version=module_version1, def_value='foo')
        deleted_spec = ParameterSpec.objects.create(id_name='deleted', type='string', module_version=module_version1)

        wf = add_new_workflow(name='Worky')
        wfm = add_new_wf_module(workflow=wf, module_version=module_version1)

        unchanged_pval = ParameterVal.objects.get(parameter_spec=unchanged_spec)
        changed_pval = ParameterVal.objects.get(parameter_spec=changed_spec)
        deleted_pval = ParameterVal.objects.get(parameter_spec=deleted_spec)

        # initialize a new module version with one unchanged, one changed, one added, one deleted
        module_version2 = ModuleVersion.objects.create(module=module)
        unchanged_spec2 = ParameterSpec.objects.create(id_name='unchanged', type='string', module_version=module_version2)
        changed_spec2 = ParameterSpec.objects.create(id_name='changed', type='integer', module_version=module_version2, def_value='42') # changed type
        added_spec2 = ParameterSpec.objects.create(id_name='added', type='string', module_version=module_version2)

        update_wfm_parameters_to_new_version(wfm, module_version2)
        self.assertEqual(wfm.module_version, module_version2)

        # still exists
        ParameterVal.objects.get(parameter_spec=unchanged_spec2)

        # changed type, reset to default
        changed_pval = ParameterVal.objects.get(parameter_spec=changed_spec2)
        self.assertEqual(changed_pval.value, '42')

        # deleted
        with self.assertRaises(ParameterVal.DoesNotExist):
            ParameterVal.objects.get(parameter_spec=deleted_spec)

        # added
        ParameterVal.objects.get(parameter_spec=added_spec2)







