from django.test import TestCase
from server.views import parameterval_detail, workflow_detail
from rest_framework.test import APIRequestFactory, force_authenticate
from server.models import ParameterVal, ParameterSpec, Module, WfModule
from rest_framework import status
from server.tests.utils import *


class ParameterValTests(LoggedInTestCase):
    def setUp(self):
        super(ParameterValTests, self).setUp()  # log in
        self.factory = APIRequestFactory()

        # Create a WfModule with one parameter of each type
        module = Module(name="TestModule")
        module.save()

        module_version = ModuleVersion()
        module_version.module = module
        module_version.save()

        self.moduleID = module.id

        stringSpec = ParameterSpec.objects.create(
            name='StringParam',
            id_name='stringparam',
            module_version=module_version,
            type= ParameterSpec.STRING,
            def_value='foo')
        integerSpec = ParameterSpec.objects.create(
            name='IntegerParam',
            id_name='integerparam',
            module_version=module_version,
            type=ParameterSpec.INTEGER,
            def_value='42')
        floatSpec = ParameterSpec.objects.create(
            name='FloatParam',
            id_name='floatparam',
            module_version=module_version,
            type=ParameterSpec.FLOAT,
            def_value='10.11')
        checkboxSpec = ParameterSpec.objects.create(
            name='CheckboxParam',
            id_name='checkboxparam',
            module_version=module_version,
            type=ParameterSpec.CHECKBOX,
            def_value='1')
        menuSpec = ParameterSpec.objects.create(
            name='MenuParam',
            id_name='menuparam',
            module_version=module_version,
            type=ParameterSpec.MENU,
            def_menu_items='Item A|Item B|Item C',
            def_value='1')  # should refer to Item B

        self.workflow = add_new_workflow(name="Test Workflow")
        self.workflowID = self.workflow.id

        self.wfmodule = WfModule.objects.create(module_version=module_version, workflow=self.workflow, order=0)
        self.wfmoduleID = self.wfmodule.id

        # set non-default values for vals in order to reveal certain types of bugs
        stringVal = ParameterVal.objects.create(parameter_spec=stringSpec, wf_module=self.wfmodule, value='fooval')
        self.stringID = stringVal.id

        integerVal = ParameterVal.objects.create(parameter_spec=integerSpec, wf_module=self.wfmodule, value='10')
        self.integerID = integerVal.id

        floatVal = ParameterVal.objects.create(parameter_spec=floatSpec, wf_module=self.wfmodule, value='3.14159')
        self.floatID = floatVal.id

        checkboxVal = ParameterVal.objects.create(parameter_spec=checkboxSpec, wf_module=self.wfmodule, value='1')
        self.checkboxID = checkboxVal.id

        menuVal = ParameterVal.objects.create(parameter_spec=menuSpec, wf_module=self.wfmodule, value='2')
        self.menuID = menuVal.id


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

    # Parameter API must return correct values
    def test_parameterval_detail_get(self):
        request = self.factory.get('/api/workflows/%d/' % self.workflowID)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = self.workflowID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Workflow')

        # workflow has correct wfmodule
        self.assertEqual(len(response.data['wf_modules']), 1)
        self.assertEqual(response.data['wf_modules'][0]['id'], self.moduleID)

        # wfmodule has correct parameters
        self.assertEqual(len(response.data['wf_modules'][0]['parameter_vals']), 5)
        valIDs = [self.stringID, self.integerID, self.floatID, self.checkboxID, self.menuID]
        param_vals = response.data['wf_modules'][0]['parameter_vals']
        responseIDs = [x['id'] for x in param_vals]
        self.assertCountEqual(responseIDs, valIDs)

        # parameters have correct types and values
        str_val = [p for p in param_vals if p['id']==self.stringID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParam')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparam')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['value'], 'fooval')

        int_val = [p for p in param_vals if p['id']==self.integerID][0]
        self.assertEqual(int_val['parameter_spec']['name'], 'IntegerParam')
        self.assertEqual(int_val['parameter_spec']['id_name'], 'integerparam')
        self.assertEqual(int_val['parameter_spec']['type'], ParameterSpec.INTEGER)
        self.assertEqual(int_val['value'], '10')

        float_val = [p for p in param_vals if p['id']==self.floatID][0]
        self.assertEqual(float_val['parameter_spec']['name'], 'FloatParam')
        self.assertEqual(float_val['parameter_spec']['id_name'], 'floatparam')
        self.assertEqual(float_val['parameter_spec']['type'], ParameterSpec.FLOAT)
        self.assertEqual(float_val['value'], '3.14159')

        checkbox_val = [p for p in param_vals if p['id']==self.checkboxID][0]
        self.assertEqual(checkbox_val['parameter_spec']['name'], 'CheckboxParam')
        self.assertEqual(checkbox_val['parameter_spec']['id_name'], 'checkboxparam')
        self.assertEqual(checkbox_val['parameter_spec']['type'], ParameterSpec.CHECKBOX)
        self.assertEqual(checkbox_val['value'], '1')

        menu_val = [p for p in param_vals if p['id'] == self.menuID][0]
        self.assertEqual(menu_val['parameter_spec']['name'], 'MenuParam')
        self.assertEqual(menu_val['parameter_spec']['id_name'], 'menuparam')
        self.assertEqual(menu_val['parameter_spec']['type'], ParameterSpec.MENU)
        self.assertEqual(menu_val['value'], '2')

    # test parameter change API
    def test_parameterval_detail_patch(self):
        old_rev  = self.workflow.revision()

        request = self.factory.patch('/api/parameters/%d/' % self.floatID,
                                   {'value': '50.456' })
        force_authenticate(request, user=self.user)
        response = parameterval_detail(request, pk=self.floatID)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        request = self.factory.get('/api/parameters/%d/' % self.floatID)
        force_authenticate(request, user=self.user)
        response = parameterval_detail(request, pk=self.floatID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['value'], '50.456')

        # changing a parameter should change the version
        self.workflow.refresh_from_db()
        self.assertNotEqual(old_rev, self.workflow.revision())




