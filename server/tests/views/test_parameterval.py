from collections import namedtuple
from unittest.mock import patch
from django.contrib.auth.models import User
from server.tests.test_parameterval import ParameterValTestHelpers
from server.models import ParameterSpec
from server.views import parameterval_detail, workflow_detail
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.tests.utils import LoggedInTestCase, load_and_add_module, \
        get_param_by_id_name


FakeSession = namedtuple('FakeSession', ['session_key'])


async def async_noop(*args, **kwargs):
    pass


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class ParameterValTests(LoggedInTestCase, ParameterValTestHelpers):
    def setUp(self):
        super().setUp()

        self.createTestWorkflow()
        self.factory = APIRequestFactory()

    def _augment_request(self, request, user: User,
                         session_key: str) -> None:
        if user:
            force_authenticate(request, user=user)
        request.session = FakeSession(session_key)

    def _build_get(self, *args, user: User=None, session_key: str='a-key',
                   **kwargs):
        request = self.factory.get(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    def _build_patch(self, *args, user: User=None, session_key: str='a-key',
                     **kwargs):
        request = self.factory.patch(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    # Workflow API must return correct values for parameters
    def test_parameterval_detail_get(self):
        # This test _actually_ tests Workflow.get. TODO move to test_workflow
        request = self._build_get('/api/workflows/%d/' % self.workflowID,
                                  user=self.user)
        response = workflow_detail(request, pk=self.workflowID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['workflow']['name'], 'Test Workflow')

        # workflow has correct wfmodule
        self.assertEqual(response.data['workflow']['wf_modules'],
                         [self.wfmoduleID])

        # wfmodule has correct parameters
        parameter_vals = \
            response.data['wfModules'][str(self.wfmoduleID)]['parameter_vals']
        self.assertEqual(len(parameter_vals), 7)
        valIDs = [self.stringID, self.stringemptyID, self.integerID,
                  self.floatID, self.checkboxID, self.menuID, self.radioID]
        self.assertEqual(set([p['id'] for p in parameter_vals]), set(valIDs))

        # parameters have correct types and values
        str_val = [p for p in parameter_vals if p['id'] == self.stringID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParam')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparam')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['parameter_spec']['placeholder'], 'placeholder')
        self.assertEqual(str_val['value'], 'fooval')

        # parameters have correct types and values
        str_val = [p for p in parameter_vals if p['id'] == self.stringemptyID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParamEmpty')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparamempty')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['parameter_spec']['placeholder'], '')
        self.assertEqual(str_val['value'], '')

        int_val = [p for p in parameter_vals if p['id']==self.integerID][0]
        self.assertEqual(int_val['parameter_spec']['name'], 'IntegerParam')
        self.assertEqual(int_val['parameter_spec']['id_name'], 'integerparam')
        self.assertEqual(int_val['parameter_spec']['type'], ParameterSpec.INTEGER)
        self.assertEqual(int_val['value'], 10)

        float_val = [p for p in parameter_vals if p['id']==self.floatID][0]
        self.assertEqual(float_val['parameter_spec']['name'], 'FloatParam')
        self.assertEqual(float_val['parameter_spec']['id_name'], 'floatparam')
        self.assertEqual(float_val['parameter_spec']['type'], ParameterSpec.FLOAT)
        self.assertEqual(float_val['value'], 3.14159)

        checkbox_val = [p for p in parameter_vals if p['id']==self.checkboxID][0]
        self.assertEqual(checkbox_val['parameter_spec']['name'], 'CheckboxParam')
        self.assertEqual(checkbox_val['parameter_spec']['id_name'], 'checkboxparam')
        self.assertEqual(checkbox_val['parameter_spec']['type'], ParameterSpec.CHECKBOX)
        self.assertEqual(checkbox_val['value'], True)

        menu_val = [p for p in parameter_vals if p['id'] == self.menuID][0]
        self.assertEqual(menu_val['parameter_spec']['name'], 'MenuParam')
        self.assertEqual(menu_val['parameter_spec']['id_name'], 'menuparam')
        self.assertEqual(menu_val['parameter_spec']['type'], ParameterSpec.MENU)
        self.assertEqual(menu_val['value'], 2)

        radio_val = [p for p in parameter_vals if p['id'] == self.radioID][0]
        self.assertEqual(radio_val['parameter_spec']['name'], 'RadioParam')
        self.assertEqual(radio_val['parameter_spec']['id_name'], 'radioparam')
        self.assertEqual(radio_val['parameter_spec']['type'], ParameterSpec.RADIO)
        self.assertEqual(radio_val['value'], 0)

    # test parameter change API
    def test_parameterval_detail_patch(self):
        old_rev  = self.workflow.revision()

        request = self._build_patch('/api/parameters/%d/' % self.floatID,
                                    {'value': '50.456' }, user=self.user)
        response = parameterval_detail(request, pk=self.floatID)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        response = self.client.get('/api/parameters/%d/' % self.floatID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['value'], 50.456)

        # changing a parameter should change the version
        self.workflow.refresh_from_db()
        self.assertNotEqual(old_rev, self.workflow.revision())
