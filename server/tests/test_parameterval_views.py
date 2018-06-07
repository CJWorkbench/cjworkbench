from server.tests.test_parameterval import ParameterValTestsBase
from server.models import ParameterVal, ParameterSpec, Module, WfModule
from server.views import parameterval_detail, workflow_detail
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.tests.utils import LoggedInTestCase, add_new_workflow, load_and_add_module, get_param_by_id_name
import mock

# Test views that ultimately get/set ParameterVal
class ParameterValTests(ParameterValTestsBase, LoggedInTestCase):

    def setUp(self):
        super(ParameterValTests, self).setUp()  # log in
        self.createTestWorkflow()
        self.factory = APIRequestFactory()

    # Workflow API must return correct values for parameters
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
        self.assertEqual(len(response.data['wf_modules'][0]['parameter_vals']), 6)
        valIDs = [self.stringID, self.stringemptyID, self.integerID, self.floatID, self.checkboxID, self.menuID]
        param_vals = response.data['wf_modules'][0]['parameter_vals']
        responseIDs = [x['id'] for x in param_vals]
        self.assertCountEqual(responseIDs, valIDs)

        # parameters have correct types and values
        str_val = [p for p in param_vals if p['id']==self.stringID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParam')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparam')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['parameter_spec']['placeholder'], 'placeholder')
        self.assertEqual(str_val['value'], 'fooval')

        # parameters have correct types and values
        str_val = [p for p in param_vals if p['id'] == self.stringemptyID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParamEmpty')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparamempty')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['parameter_spec']['placeholder'], '')
        self.assertEqual(str_val['value'], '')

        int_val = [p for p in param_vals if p['id']==self.integerID][0]
        self.assertEqual(int_val['parameter_spec']['name'], 'IntegerParam')
        self.assertEqual(int_val['parameter_spec']['id_name'], 'integerparam')
        self.assertEqual(int_val['parameter_spec']['type'], ParameterSpec.INTEGER)
        self.assertEqual(int_val['value'], 10)

        float_val = [p for p in param_vals if p['id']==self.floatID][0]
        self.assertEqual(float_val['parameter_spec']['name'], 'FloatParam')
        self.assertEqual(float_val['parameter_spec']['id_name'], 'floatparam')
        self.assertEqual(float_val['parameter_spec']['type'], ParameterSpec.FLOAT)
        self.assertEqual(float_val['value'], 3.14159)

        checkbox_val = [p for p in param_vals if p['id']==self.checkboxID][0]
        self.assertEqual(checkbox_val['parameter_spec']['name'], 'CheckboxParam')
        self.assertEqual(checkbox_val['parameter_spec']['id_name'], 'checkboxparam')
        self.assertEqual(checkbox_val['parameter_spec']['type'], ParameterSpec.CHECKBOX)
        self.assertEqual(checkbox_val['value'], True)

        menu_val = [p for p in param_vals if p['id'] == self.menuID][0]
        self.assertEqual(menu_val['parameter_spec']['name'], 'MenuParam')
        self.assertEqual(menu_val['parameter_spec']['id_name'], 'menuparam')
        self.assertEqual(menu_val['parameter_spec']['type'], ParameterSpec.MENU)
        self.assertEqual(menu_val['value'], 2)

    # test parameter change API
    def test_parameterval_detail_patch(self):
        old_rev  = self.workflow.revision()

        request = self.factory.patch('/api/parameters/%d/' % self.floatID,
                                   {'value': '50.456' })
        force_authenticate(request, user=self.user)
        response = parameterval_detail(request, pk=self.floatID)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        response = self.client.get('/api/parameters/%d/' % self.floatID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['value'], 50.456)

        # changing a parameter should change the version
        self.workflow.refresh_from_db()
        self.assertNotEqual(old_rev, self.workflow.revision())

    # if we press enter on the url field of loadurl, also "press" the check button
    def test_parameterval_detail_patch_fetch(self):
        wfm = load_and_add_module('loadurl')  # creates new workflow too
        url_param = get_param_by_id_name('url')

        with mock.patch('server.modules.loadurl.LoadURL.event') as event_call:

            request = self.factory.patch('/api/parameters/%d/' % url_param.id, {'value': '50.456', 'pressed_enter':True })
            force_authenticate(request, user=self.user)
            response = parameterval_detail(request, pk=url_param.id)
            self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

            # should have made an call to the LoadURL event handler
            self.assertIs(event_call.call_count, 1)
