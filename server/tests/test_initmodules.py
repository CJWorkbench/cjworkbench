# test module (re)loading
from server.models import ParameterSpec, Module, Workflow
from server.initmodules import load_module_from_dict
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

        # Create a wf_module that references this module.
        wf = Workflow.objects.create()
        tab = wf.tabs.create(position=0)
        wfm = tab.wf_modules.create(
            order=0,
            module_version=m1,
            params=m1.get_default_params()
        )

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
        wfm.refresh_from_db()
        self.assertEqual(wfm.params, m1.get_default_params())

        # load same version again, should re-use module_version
        m3 = load_module_from_dict(mini_module2)
        self.assertEqual(m2.id, m3.id)

        # load a different version
        mini_module4 = copy.deepcopy(mini_module2)
        mini_module4['source_version'] = 'f0f0beef'
        m4 = load_module_from_dict(mini_module4)
        self.assertNotEqual(m3.id, m4.id)

    # # Checks that re-importing an internal module (same id_name) overwrites the
    # # old fields
    # def test_reload_internal_module(self):
    #     # we should be starting with no modules
    #     self.assertEqual(len(Module.objects.all()), 0)

    #     m1 = load_module_from_dict(LoadCsv)
    #     ParameterSpec.objects.get(id_name='url')
    #     ParameterSpec.objects.get(id_name='fetch')
    #     # internal modules get this version
    #     self.assertEqual(m1.source_version_hash, '1.0')

    #     radio_spec = ParameterSpec.objects.get(id_name='radio_options')
    #     self.assertEqual(radio_spec.type, ParameterSpec.RADIO)
    #     self.assertEqual(radio_spec.def_value, '1')
    #     self.assertEqual(radio_spec.items, 'Cheese|Chocolate|Pudding')

    #     # create two wf_modules that reference this module
    #     workflow = Workflow.objects.create()
    #     tab = workflow.tabs.create(position=0)
    #     tab.wf_modules.create(
    #         module_version=m1,
    #         order=0,
    #         params=m1.get_default_params()
    #     )
    #     tab.wf_modules.create(
    #         module_version=m1,
    #         order=0,
    #         params=m1.get_default_params()
    #     )

    #     # load the revised module, check that it ends up with the same primary
    #     # key
    #     m2 = load_module_from_dict(LoadCsv2)
    #     self.assertEqual(m1.id, m2.id)
    #     self.assertEqual(m2.module.help_url, '')

    #     # button pspec should be gone
    #     with self.assertRaises(ParameterSpec.DoesNotExist):
    #         ParameterSpec.objects.get(id_name='fetch')

    #     # parametervals should now point to spec with new type, default value
    #     # and have value=default value because type changed
    #     self.assertEqual(ParameterSpec.objects.filter(id_name='url').count(),
    #                      1)
    #     url_spec2 = ParameterSpec.objects.get(id_name='url')
    #     self.assertEqual(url_spec2.type, ParameterSpec.INTEGER)
    #     self.assertEqual(url_spec2.order, 1)
    #     self.assertEqual(url_spec2.def_value, '42')

    #     # new Menu parameter should exist
    #     menu_spec = ParameterSpec.objects.get(id_name='caketype')
    #     self.assertEqual(menu_spec.type, ParameterSpec.MENU)
    #     self.assertEqual(menu_spec.def_value, '1')
    #     self.assertEqual(menu_spec.items, 'Cheese|Chocolate')
    #     self.assertEqual(menu_spec.order, 0)

    #     # load the old one again, just for kicks (and to test updating a
    #     # previously updated module_version)
    #     m2 = load_module_from_dict(LoadCsv)

    # A brief check of conditional UI, in that the JSON can be stored and
    # retrieved correctly.
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
        self.assertEqual(cond_spec_visibility, {
            'id_name': 'cond_menu',
            'value': 'cond1|cond3',
        })

    def test_condui_invalid(self):
        # A very barebones module to test conditional UI loading
        cond_ui = {
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
                        # missing 'value'
                    }
                }
            ]
        }

        with self.assertRaises(ValueError):
            # this also tests that db is still valid if load fails
            load_module_from_dict(cond_ui)
