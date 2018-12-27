# test module (re)loading
from server.models import ParameterVal, ParameterSpec, Module, \
        Workflow, ModuleVersion
from server.initmodules import load_module_from_dict, \
        update_wfm_parameters_to_new_version
from server.tests.utils import DbTestCase
import json
import copy


LoadCsv = {
    'name': 'Load CSV',
    'id_name': 'loadcsv',
    'category': 'Sources',
    'help_url': 'http://help.com/help',
    'parameters': [
        {
            'name': 'URL',
            'id_name': 'url',
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
            'id_name': 'fetch',
            'type': 'button'
        },
        {
            'name': 'No default',
            'id_name': 'nodefault',
            'type': 'string',
            'multiline': True,
        },
        {
            'name': 'Do it checkbox',
            'id_name': 'doitcheckbox',
            'type': 'checkbox',
            'default': True
        },
        {
            'name': 'Radio Option',
            'id_name': 'radio_options',
            'type': 'radio',
            'radio_items': 'Cheese|Chocolate|Pudding',
            'default': 1
        },
    ]
}


# a new version of LoadCSV that deletes one parameter, changes the type and order of another,
# and adds a new one, and tests menu param
LoadCsv2 = {
    'name': 'Load CSV RELOADED',
    'id_name': 'loadcsv',
    'category': 'Sources',
    'parameters': [
        {
            'name': 'Cake type',
            'id_name': 'caketype',
            'type': 'menu',
            'menu_items': 'Cheese|Chocolate',
            'default': 1
        },
        {
            'name': 'URL',
            'id_name': 'url',
            'type': 'integer',
            'default': '42'
        }
    ]
}


class InitmoduleTests(DbTestCase):
    def test_load_valid(self):
        load_module_from_dict(LoadCsv)

        # basic properties
        self.assertEqual(len(Module.objects.all()), 1)
        m = Module.objects.all()[0]
        self.assertEqual(m.name, 'Load CSV')
        self.assertEqual(m.id_name, 'loadcsv')
        self.assertEqual(m.help_url, 'http://help.com/help')

        # parameters
        pspecs = ParameterSpec.objects.all()
        self.assertEqual(len(pspecs), 6)

        url_spec = ParameterSpec.objects.get(id_name='url')
        self.assertEqual(url_spec.name, 'URL')
        self.assertEqual(url_spec.id_name, 'url')
        self.assertEqual(url_spec.type, ParameterSpec.STRING)
        self.assertEqual(url_spec.def_value, 'http://foo.com')
        self.assertEqual(url_spec.multiline, False)
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
        self.assertEqual(button_spec.order, 2)

        # check missing default has a default, and that multiline works
        nodef_spec = ParameterSpec.objects.get(id_name='nodefault')
        self.assertEqual(nodef_spec.type, ParameterSpec.STRING)
        self.assertEqual(nodef_spec.def_value, '')
        self.assertEqual(nodef_spec.multiline, True)

        # Make sure checkbox loads with correct default value
        # This tests boolean -> string conversion (JSON is boolean,
        # def_value is string)
        cb_spec = ParameterSpec.objects.get(id_name='doitcheckbox')
        self.assertEqual(cb_spec.type, ParameterSpec.CHECKBOX)
        self.assertEqual(cb_spec.def_value, 'True')

    # we should bail when keys are missing
    def test_missing_keys(self):
        module_keys = ['name', 'id_name', 'category']
        for k in module_keys:
            missing = copy.deepcopy(LoadCsv)
            del missing[k]
            with self.assertRaises(ValueError):
                load_module_from_dict(missing)

        param_keys = ['name', 'id_name', 'type']
        for k in param_keys:
            missing = copy.deepcopy(LoadCsv)
            del missing['parameters'][0][k]
            with self.assertRaises(ValueError):
                load_module_from_dict(missing)

    # Reloading an external module should create a new module_version,
    # but not add new parameters
    def test_reload_external_module(self):
        # source_version => external
        mini_module = {
            'name': 'Test',
            'id_name': 'test',
            'category': 'Cats',
            'source_version': 'f00dbeef',
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

        # Create a wf_module that references this module. Should create a new
        # ParameterVal
        wf = Workflow.objects.create()
        tab = wf.tabs.create(position=0)
        wfm = tab.wf_modules.create(order=0, module_version=m1)
        wfm.create_parametervals()

        mini_module2 = {
            'name': 'Test',
            'id_name': 'test',
            'category': 'Cats',
            'source_version': 'deadbeef',
            'parameters': [
                {
                    'name': 'URL',
                    'id_name': 'url',
                    'type': 'string',
                },
                {
                    'name': 'New Integer',
                    'id_name': 'newint',
                    'type': 'integer'
                }
            ]
        }

        # loading new definition should create new module_version, should not
        # add/alter old parameter values
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

    # Checks that re-importing an internal module (same id_name) overwrites the
    # old fields and existing ParameterVals are updated
    def test_reload_internal_module(self):
        # we should be starting with no modules
        self.assertEqual(len(Module.objects.all()), 0)

        m1 = load_module_from_dict(LoadCsv)
        url_spec1 = ParameterSpec.objects.get(id_name='url')
        ParameterSpec.objects.get(id_name='fetch')
        # internal modules get this version
        self.assertEqual(m1.source_version_hash, '1.0')

        radio_spec = ParameterSpec.objects.get(id_name='radio_options')
        self.assertEqual(radio_spec.type, ParameterSpec.RADIO)
        self.assertEqual(radio_spec.def_value, '1')
        self.assertEqual(radio_spec.items, 'Cheese|Chocolate|Pudding')

        # create wf_modules in two different workflows that reference this
        # module
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wfm1 = tab.wf_modules.create(module_version=m1, order=0)
        wfm1.create_parametervals()
        wfm2 = tab.wf_modules.create(module_version=m1, order=0)
        wfm2.create_parametervals()

        # precondition: corresponding parameter val exists for each wfm with
        # correct default also tested in test_wfmodule.py but whatevs, won't
        # hurt
        url_pval1 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm1)
        self.assertEqual(url_pval1.value, 'http://foo.com')
        url_pval2 = ParameterVal.objects.get(parameter_spec=url_spec1, wf_module=wfm2)
        self.assertEqual(url_pval2.value, 'http://foo.com')

        # load the revised module, check that it ends up with the same primary key
        m2 = load_module_from_dict(LoadCsv2)
        self.assertEqual(m1.id, m2.id)
        self.assertEqual(m2.module.help_url, '')

        # button pspec should be gone
        with self.assertRaises(ParameterSpec.DoesNotExist):
            ParameterSpec.objects.get(id_name='fetch')

        # parametervals should now point to spec with new type, default value
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
        self.assertEqual(menu_spec.items, 'Cheese|Chocolate')
        self.assertEqual(menu_spec.order, 0)
        menu_pval1 = ParameterVal.objects.get(parameter_spec=menu_spec, wf_module=wfm1)
        self.assertEqual(menu_pval1.value, '1')
        menu_pval2 = ParameterVal.objects.get(parameter_spec=menu_spec, wf_module=wfm2)
        self.assertEqual(menu_pval2.value, '1')

        # load the old one again, just for kicks (and to test updating a previously updated module_version)
        m2 = load_module_from_dict(LoadCsv)


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

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wfm = tab.wf_modules.create(module_version=module_version1, order=0)
        wfm.create_parametervals()

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

        # changed type, reset to default
        changed_pval.refresh_from_db()
        self.assertEqual(changed_pval.value, '42')

        # deleted
        with self.assertRaises(ParameterVal.DoesNotExist):
            deleted_pval.refresh_from_db()

        # added
        ParameterVal.objects.get(parameter_spec=added_spec2)

    def test_update_module_keep_compatible_types(self):
        # Test specs that change type but are still compatible (ie. Menu to Radio)
        module = Module.objects.create()
        module_version3 = ModuleVersion.objects.create(module=module)
        unchanged_spec3 = ParameterSpec.objects.create(id_name='unchanged', type='menu', module_version=module_version3,
                                                       items='Option 1|Option 2|Option 3', def_value='0')
        changed_spec3 = ParameterSpec.objects.create(id_name='changed', type='menu', module_version=module_version3,
                                                       items='Option 1|Option 2|Option 3', def_value='0')


        wf2 = Workflow.objects.create(name='Ancient Workflow')
        tab = wf2.tabs.create(position=0)
        wfm2 = tab.wf_modules.create(order=0, module_version=module_version3)
        wfm2.create_parametervals({'unchanged': 2, 'changed': 2})

        unchanged_pval = wfm2.parameter_vals.get(parameter_spec=unchanged_spec3)
        changed_pval = wfm2.parameter_vals.get(parameter_spec=changed_spec3)

        module_version4 = ModuleVersion.objects.create(module=module)
        unchanged_spec4 = ParameterSpec.objects.create(id_name='unchanged', type='radio', module_version=module_version4,
                                                       items='Option 1|Option 2|Option 3')
        changed_spec4 = ParameterSpec.objects.create(id_name='changed', type='radio', module_version=module_version4,
                                                     items='Option 1|Option 2', def_value='0')

        update_wfm_parameters_to_new_version(wfm2, module_version4)
        self.assertEqual(wfm2.module_version, module_version4)

        # changed type, but items the same. Value should stay the same.
        unchanged_pval.refresh_from_db()
        self.assertEqual(unchanged_pval.value, '2')

        # changed type, but items different. Value should reset to default.
        changed_pval.refresh_from_db()
        self.assertEqual(changed_pval.value, '0')
