from server.models import ParameterSpec, Workflow
from server.tests.utils import DbTestCase, add_new_module_version, \
        add_new_workflow


# Mixin class sets up a workflow for testing, shared between this file
# and test_parameterval_views.py
class ParameterValTestHelpers:
    def createTestWorkflow(self):
        # Create a WfModule with one parameter of each type

        self.module_version = add_new_module_version("TestModule")
        self.moduleID = self.module_version.module.id

        ParameterSpec.objects.create(
            name='StringParam',
            id_name='stringparam',
            module_version=self.module_version,
            type=ParameterSpec.STRING,
            def_value='foo',
            placeholder='placeholder')
        ParameterSpec.objects.create(
            name='StringParamEmpty',
            id_name='stringparamempty',
            module_version=self.module_version,
            type=ParameterSpec.STRING)
        ParameterSpec.objects.create(
            name='IntegerParam',
            id_name='integerparam',
            module_version=self.module_version,
            type=ParameterSpec.INTEGER,
            def_value='42')
        ParameterSpec.objects.create(
            name='FloatParam',
            id_name='floatparam',
            module_version=self.module_version,
            type=ParameterSpec.FLOAT,
            def_value='10.11')
        ParameterSpec.objects.create(
            name='CheckboxParam',
            id_name='checkboxparam',
            module_version=self.module_version,
            type=ParameterSpec.CHECKBOX,
            def_value='1')
        ParameterSpec.objects.create(
            name='MenuParam',
            id_name='menuparam',
            module_version=self.module_version,
            type=ParameterSpec.MENU,
            items='Item A|Item B|Item C',
            def_value='1')  # should refer to Item B
        ParameterSpec.objects.create(
            name='RadioParam',
            id_name='radioparam',
            module_version=self.module_version,
            type=ParameterSpec.RADIO,
            items='Item A|Item B|Item C',
            def_value='0')  # should refer to Item A

        self.workflow = Workflow.objects.create()
        self.tab = self.workflow.tabs.create(position=0)
        self.wfmodule = self.tab.wf_modules.create(
            module_version=self.module_version,
            order=0,
            # set non-default values for vals in order to reveal certain types
            # of bugs
            #
            # [2018-12-28, adamhooper] ^^ what types of bugs?
            params={
                'stringparam': 'fooval',
                'stringparamempty': '',
                'integerparam': 10,
                'floatparam': 3.14159,
                'checkboxparam': True,
                'menuparam': 2,
                'radioparam': 0,
            }
        )


class ParameterValTests(DbTestCase, ParameterValTestHelpers):
    def setUp(self):
        super().setUp()

        self.createTestWorkflow()

    def secret_val(self):
        spec = ParameterSpec.objects.create(
            name='SecretParam',
            id_name='asecret',
            module_version=self.module_version,
            type=ParameterSpec.SECRET
        )
        val = self.wfmodule.parameter_vals.create(parameter_spec=spec,
                                                  value='')
        return val

    # Value retrieval methods must return correct values and enforce type
    def test_parameter_get_values(self):
        params = self.wfmodule.get_params()

        # current values are as set when created
        s = params.get_param_string('stringparam')
        self.assertEqual(s, 'fooval')

        se = params.get_param_string('stringparamempty')
        self.assertEqual(se, '')

        i = params.get_param_integer('integerparam')
        self.assertEqual(i, 10)

        f = params.get_param_float('floatparam')
        self.assertEqual(f, 3.14159)

        t = params.get_param_checkbox('checkboxparam')
        self.assertEqual(t, True)

        m = params.get_param_menu_idx('menuparam')
        self.assertEqual(m, 2)

        m = params.get_param_radio_idx('radioparam')
        self.assertEqual(m, 0)

        # Retrieving value of wrong type should raise exception
        with self.assertRaises(ValueError):
            params.get_param_string('integerparam')
        with self.assertRaises(ValueError):
            params.get_param_string('floatparam')
        with self.assertRaises(ValueError):
            params.get_param_string('checkboxparam')
        with self.assertRaises(ValueError):
            params.get_param_integer('stringparam')
        with self.assertRaises(ValueError):
            params.get_param_checkbox('stringparam')
        with self.assertRaises(ValueError):
            params.get_param_checkbox('menuparam')

        # error if no param by that name
        with self.assertRaises(KeyError):
            params.get_param_string('FooParam')

    def test_secret_default_none(self):
        self.assertIs(self.secret_val().get_value(), None)

    def test_secret_set_get_value(self):
        val = self.secret_val()
        val.set_value({ 'name': 'foo', 'secret': { 'bar': 'baz' } })

        self.assertEqual(val.get_value(), { 'name': 'foo' })
        self.assertEqual(val.get_secret(), { 'bar': 'baz' })

    def test_secret_check_set_value(self):
        val = self.secret_val()
        with self.assertRaises(ValueError):
            val.set_value({ 'namex': 'foo', 'secret': { 'bar': 'baz' } }) # no name
        with self.assertRaises(ValueError):
            val.set_value({ 'name': '', 'secret': { 'bar': 'baz' } }) # empty name
        with self.assertRaises(ValueError):
            val.set_value({ 'name': 'foo', 'secret': '' }) # no secret

    def test_secret_set_value_empty(self):
        val = self.secret_val()
        val.set_value({ 'name': 'foo', 'secret': 'foo' })
        val.set_value(None)
        self.assertIs(val.get_value(), None)

    def test_secret_not_duplicated(self):
        val1 = self.secret_val()
        val1.set_value({ 'name': 'foo', 'secret': 'foo' })

        workflow2 = add_new_workflow("Test Workflow 2")
        tab2 = workflow2.tabs.create(position=0)
        wfmodule2 = tab2.wf_modules.create(module_version=self.module_version,
                                           order=0)

        val2 = val1.duplicate(wfmodule2)
        self.assertEqual(val2.get_value(), None)
        self.assertEqual(val2.get_secret(), None)
