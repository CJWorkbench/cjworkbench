from django.test import TestCase
from server.models import ParameterVal, ParameterSpec, Module, WfModule, ModuleVersion
from server.tests.utils import *

# Base class sets up a workflow for testing, shared between this file and test_parameterval_views.py
class ParameterValTestsBase(TestCase):

    def createTestWorkflow(self):
        # Create a WfModule with one parameter of each type

        self.module_version = add_new_module_version("TestModule")
        self.moduleID = self.module_version.module.id

        stringSpec = ParameterSpec.objects.create(
            name='StringParam',
            id_name='stringparam',
            module_version=self.module_version,
            type= ParameterSpec.STRING,
            def_value='foo')
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
            def_menu_items='Item A|Item B|Item C',
            def_value='1')  # should refer to Item B

        self.workflow = add_new_workflow(name="Test Workflow")
        self.workflowID = self.workflow.id

        self.wfmodule = WfModule.objects.create(module_version=self.module_version, workflow=self.workflow, order=0)
        self.wfmoduleID = self.wfmodule.id

        # set non-default values for vals in order to reveal certain types of bugs
        stringVal = ParameterVal.objects.create(parameter_spec=stringSpec, wf_module=self.wfmodule, value='fooval')
        self.stringID = stringVal.id

        integerVal = ParameterVal.objects.create(parameter_spec=integerSpec, wf_module=self.wfmodule, value='10')
        self.integerID = integerVal.id

        floatVal = ParameterVal.objects.create(parameter_spec=floatSpec, wf_module=self.wfmodule, value='3.14159')
        self.floatID = floatVal.id

        checkboxVal = ParameterVal.objects.create(parameter_spec=checkboxSpec, wf_module=self.wfmodule, value='True')
        self.checkboxID = checkboxVal.id

        menuVal = ParameterVal.objects.create(parameter_spec=menuSpec, wf_module=self.wfmodule, value='2')
        self.menuID = menuVal.id


# Unit tests on ParameterVal
class ParameterValTests(ParameterValTestsBase):

    def setUp(self):
        self.createTestWorkflow()


    # Value retrieval methods must return correct values and enforce type
    def test_parameter_get_values(self):

        # current values are as set when created
        s = self.wfmodule.get_param_string('stringparam')
        self.assertEqual(s, 'fooval')

        i = self.wfmodule.get_param_integer('integerparam')
        self.assertEqual(i, 10)

        f = self.wfmodule.get_param_float('floatparam')
        self.assertEqual(f, 3.14159)

        t = self.wfmodule.get_param_checkbox('checkboxparam')
        self.assertEqual(t, True)

        m = self.wfmodule.get_param_menu_idx('menuparam')
        self.assertEqual(m, 2)

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

        # error if no param by that name
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('FooParam')


    def test_duplicate(self):
        # Create a new WfModule of the same type, that has no parametervals yet
        # This is the context where duplicate is normally called, when duplicating a WfModule
        workflow2 = add_new_workflow("Test Workflow 2")
        wfmodule2 = WfModule.objects.create(module_version=self.module_version, workflow=workflow2, order=0)

        sp = ParameterVal.objects.get(pk=self.stringID)
        spd = sp.duplicate(wfmodule2)
        self.assertEqual(spd.wf_module, wfmodule2)
        self.assertEqual(sp.parameter_spec, spd.parameter_spec)
        self.assertEqual(sp.value, spd.value)
        self.assertEqual(sp.menu_items, spd.menu_items)
        self.assertEqual(sp.visible, spd.visible)
        self.assertEqual(sp.order, spd.order)
