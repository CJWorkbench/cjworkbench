from server.models import ParameterVal, ParameterSpec, WfModule
from server.tests.utils import DbTestCase, add_new_module_version, \
        add_new_workflow


# Mixin class sets up a workflow for testing, shared between this file
# and test_parameterval_views.py
class ParameterValTestHelpers:
    def createTestWorkflow(self):
        # Create a WfModule with one parameter of each type

        self.module_version = add_new_module_version("TestModule")
        self.moduleID = self.module_version.module.id

        stringSpec = ParameterSpec.objects.create(
            name='StringParam',
            id_name='stringparam',
            module_version=self.module_version,
            type= ParameterSpec.STRING,
            def_value='foo',
            placeholder='placeholder')
        stringSpecEmpty = ParameterSpec.objects.create(
            name='StringParamEmpty',
            id_name='stringparamempty',
            module_version=self.module_version,
            type=ParameterSpec.STRING)
        integerSpec = ParameterSpec.objects.create(
            name='IntegerParam',
            id_name='integerparam',
            module_version=self.module_version,
            type=ParameterSpec.INTEGER,
            def_value='42')
        floatSpec = ParameterSpec.objects.create(
            name='FloatParam',
            id_name='floatparam',
            module_version=self.module_version,
            type=ParameterSpec.FLOAT,
            def_value='10.11')
        checkboxSpec = ParameterSpec.objects.create(
            name='CheckboxParam',
            id_name='checkboxparam',
            module_version=self.module_version,
            type=ParameterSpec.CHECKBOX,
            def_value='1')
        menuSpec = ParameterSpec.objects.create(
            name='MenuParam',
            id_name='menuparam',
            module_version=self.module_version,
            type=ParameterSpec.MENU,
            def_items='Item A|Item B|Item C',
            def_value='1')  # should refer to Item B
        radioSpec = ParameterSpec.objects.create(
            name='RadioParam',
            id_name='radioparam',
            module_version=self.module_version,
            type=ParameterSpec.RADIO,
            def_items='Item A|Item B|Item C',
            def_value='0')  # should refer to Item A

        self.workflow = add_new_workflow(name="Test Workflow")
        self.workflowID = self.workflow.id

        self.wfmodule = WfModule.objects.create(module_version=self.module_version, workflow=self.workflow, order=0)
        self.wfmoduleID = self.wfmodule.id

        # set non-default values for vals in order to reveal certain types of bugs
        stringVal = ParameterVal.objects.create(parameter_spec=stringSpec, wf_module=self.wfmodule, value='fooval')
        self.stringID = stringVal.id

        emptyStringVal = ParameterVal.objects.create(parameter_spec=stringSpecEmpty, wf_module=self.wfmodule)
        self.stringemptyID = emptyStringVal.id

        integerVal = ParameterVal.objects.create(parameter_spec=integerSpec, wf_module=self.wfmodule, value='10')
        self.integerID = integerVal.id

        floatVal = ParameterVal.objects.create(parameter_spec=floatSpec, wf_module=self.wfmodule, value='3.14159')
        self.floatID = floatVal.id

        checkboxVal = ParameterVal.objects.create(parameter_spec=checkboxSpec, wf_module=self.wfmodule, value='True')
        self.checkboxID = checkboxVal.id

        menuVal = ParameterVal.objects.create(parameter_spec=menuSpec, wf_module=self.wfmodule, value='2', items=menuSpec.def_items)
        self.menuID = menuVal.id

        radioVal = ParameterVal.objects.create(parameter_spec=radioSpec, wf_module=self.wfmodule, value='0', items=radioSpec.def_items)
        self.radioID = radioVal.id


# Unit tests on ParameterVal
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
        val = ParameterVal.objects.create(parameter_spec=spec,
                                          wf_module=self.wfmodule, value='')
        return val

    # Value retrieval methods must return correct values and enforce type
    def test_parameter_get_values(self):

        # current values are as set when created
        s = self.wfmodule.get_param_string('stringparam')
        self.assertEqual(s, 'fooval')

        se = self.wfmodule.get_param_string('stringparamempty')
        self.assertEqual(se, '')

        i = self.wfmodule.get_param_integer('integerparam')
        self.assertEqual(i, 10)

        f = self.wfmodule.get_param_float('floatparam')
        self.assertEqual(f, 3.14159)

        t = self.wfmodule.get_param_checkbox('checkboxparam')
        self.assertEqual(t, True)

        m = self.wfmodule.get_param_menu_idx('menuparam')
        self.assertEqual(m, 2)

        m = self.wfmodule.get_param_menu_string('menuparam')
        self.assertEqual(m, 'Item C')

        m = self.wfmodule.get_param_radio_idx('radioparam')
        self.assertEqual(m, 0)

        m = self.wfmodule.get_param_radio_string('radioparam')
        self.assertEqual(m, 'Item A')

        # Retrieving value of wrong type should raise exception
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('integerparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('floatparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('checkboxparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_integer('stringparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_checkbox('stringparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_checkbox('menuparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_radio_string('menuparam')

        # error if no param by that name
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('FooParam')

    def test_duplicate(self):
        # Create a new WfModule of the same type, that has no parametervals yet
        # This is the context where duplicate is normally called, when
        # duplicating a WfModule
        workflow2 = add_new_workflow("Test Workflow 2")
        wfmodule2 = WfModule.objects.create(module_version=self.module_version, workflow=workflow2, order=0)

        sp = ParameterVal.objects.get(pk=self.stringID)
        spd = sp.duplicate(wfmodule2)
        self.assertEqual(spd.wf_module, wfmodule2)
        self.assertEqual(sp.parameter_spec, spd.parameter_spec)
        self.assertEqual(sp.value, spd.value)
        self.assertEqual(sp.items, spd.items)
        self.assertEqual(sp.visible, spd.visible)
        self.assertEqual(sp.order, spd.order)


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
        wfmodule2 = WfModule.objects.create(module_version=self.module_version, workflow=workflow2, order=0)

        val2 = val1.duplicate(wfmodule2)
        self.assertEqual(val2.get_value(), None)
        self.assertEqual(val2.get_secret(), None)
