from django.test import TestCase
from django.test import TestCase
from server.views import workflow_list, workflow_addmodule, workflow_detail, module_list, parameterval_detail
from server.views.WfModule import wfmodule_detail,wfmodule_render
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.models import ParameterVal, ParameterSpec, Module, WfModule, Workflow
from server.dispatch import test_data_table
from server.tests.utils import *
import pandas as pd
import json

class WorkflowTests(LoggedInTestCase):
    def setUp(self):
        super(WorkflowTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        add_new_workflow('Workflow 1')
        add_new_workflow('Workflow 2')
        add_new_module('Module 1')
        add_new_module('Module 2')
        add_new_module('Module 3')

    def test_workflow_list_get(self):
        request = self.factory.get('/api/workflows/')
        force_authenticate(request, user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Workflow 1')
        self.assertEqual(response.data[1]['name'], 'Workflow 2')

    def test_workflow_list_post(self):
        request = self.factory.post('/api/workflows/', {'name': 'Workflow 3'})
        force_authenticate(request, user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), 3)
        self.assertEqual(Workflow.objects.filter(name='Workflow 3').count(), 1)

    def test_workflow_addmodule_put(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 2').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 3').id,
                                    'insertBefore': 1})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(list(WfModule.objects.values_list('module', flat=True)),
                         [Module.objects.get(name='Module 2').id,
                          Module.objects.get(name='Module 3').id,
                          Module.objects.get(name='Module 1').id])

        request = self.factory.put('/api/workflows/%d/addmodule/' % 10000,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        request = self.factory.put('/api/workflows/%d/addmodule/' % Workflow.objects.get(name='Workflow 1').id,
                                   {'moduleID': 10000,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=Workflow.objects.get(name='Workflow 1').id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workflow_detail_get(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.get('/api/workflows/%d/' % pk_workflow)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Workflow 1')

    def test_workflow_detail_get(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.get('/api/workflows/%d/' % pk_workflow)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Workflow 1')

        # bad ID should give 404
        request = self.factory.get('/api/workflows/%d/' % 10000)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = 10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # not authenticated should give 403
        request = self.factory.get('/api/workflows/%d/' % pk_workflow)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_workflow_detail_patch(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 2').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 3').id,
                                    'insertBefore': 1})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.patch('/api/workflows/%d/' % pk_workflow, data=[{'id': 1, 'order': 1},
                                                                               {'id': 2, 'order': 2},
                                                                               {'id': 3, 'order': 3}], format='json')
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(WfModule.objects.values_list('id', flat=True)), [1, 2, 3])

    def test_workflow_detail_delete(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.delete('/api/workflows/%d/' % pk_workflow)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name='Workflow 1').count(), 0)



class ModuleTests(LoggedInTestCase):
    def setUp(self):
        super(ModuleTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        self.add_new_module('Module 1')
        self.add_new_module('Module 2')
        self.add_new_module('Module 3')

    def add_new_module(self, name):
        module = Module(name=name, id_name=name+'_internal', dispatch=name+'_dispatch')
        module.save()

    def test_module_list_get(self):
        request = self.factory.get('/api/modules/')
        force_authenticate(request, user=User.objects.first())
        response = module_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Module 1')
        self.assertEqual(response.data[1]['name'], 'Module 2')
        self.assertEqual(response.data[2]['name'], 'Module 3')


class ParameterValTests(LoggedInTestCase):
    def setUp(self):
        super(ParameterValTests, self).setUp()  # log in
        self.factory = APIRequestFactory()

        # Create a WfModule with one parameter of each type
        module = Module(name="TestModule")
        module.save()
        self.moduleID = module.id

        stringSpec = ParameterSpec.objects.create(name="StringParam", id_name="stringparam", module=module, type= ParameterSpec.STRING, def_string='foo')
        numberSpec = ParameterSpec.objects.create(name="NumberParam", id_name="numberparam", module=module, type=ParameterSpec.NUMBER, def_number=10.11)
        checkboxSpec = ParameterSpec.objects.create(name="CheckboxParam", id_name="checkboxparam", module=module, type=ParameterSpec.CHECKBOX, def_checkbox=True)

        self.workflow = add_new_workflow(name="Test Workflow")
        self.workflowID = self.workflow.id

        self.wfmodule = WfModule.objects.create(module=module, workflow=self.workflow, order=0)
        self.wfmoduleID = self.wfmodule.id

        # set non-default values for vals in order to reveal certain types of bugs
        stringVal = ParameterVal.objects.create(parameter_spec=stringSpec, wf_module=self.wfmodule, string='fooval')
        self.stringID = stringVal.id

        numberVal = ParameterVal.objects.create(parameter_spec=numberSpec, wf_module=self.wfmodule, number=10.11)
        self.numberID = numberVal.id

        checkboxVal = ParameterVal.objects.create(parameter_spec=checkboxSpec, wf_module=self.wfmodule, checkbox='True')
        self.checkboxID = checkboxVal.id

    # Value retrieval methods must return correct values and enforce type
    def test_parameter_get_values(self):
        s = self.wfmodule.get_param_string('stringparam')
        self.assertEqual(s, 'fooval')

        n = self.wfmodule.get_param_number('numberparam')
        self.assertEqual(n, 10.11)

        t = self.wfmodule.get_param_checkbox('checkboxparam')
        self.assertEqual(t, True)

        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('numberparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('checkboxparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_number('stringparam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_checkbox('stringparam')

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
        self.assertEqual(response.data['wf_modules'][0]['module']['id'], self.moduleID)

        # wfmodule has correct parameters
        self.assertEqual(len(response.data['wf_modules'][0]['parameter_vals']), 3)
        valIDs = [self.stringID, self.numberID, self.checkboxID]
        param_vals = response.data['wf_modules'][0]['parameter_vals']
        responseIDs = [x['id'] for x in param_vals]
        self.assertCountEqual(responseIDs, valIDs)

        # parameters have correct types and values
        str_val = [p for p in param_vals if p['id']==self.stringID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParam')
        self.assertEqual(str_val['parameter_spec']['id_name'], 'stringparam')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['string'], 'fooval')

        num_val = [p for p in param_vals if p['id']==self.numberID][0]
        self.assertEqual(num_val['parameter_spec']['name'], 'NumberParam')
        self.assertEqual(num_val['parameter_spec']['id_name'], 'numberparam')
        self.assertEqual(num_val['parameter_spec']['type'], ParameterSpec.NUMBER)
        self.assertEqual(num_val['number'], 10.11)

        checkbox_val = [p for p in param_vals if p['id']==self.checkboxID][0]
        self.assertEqual(checkbox_val['parameter_spec']['name'], 'CheckboxParam')
        self.assertEqual(checkbox_val['parameter_spec']['id_name'], 'checkboxparam')
        self.assertEqual(checkbox_val['parameter_spec']['type'], ParameterSpec.CHECKBOX)
        self.assertEqual(checkbox_val['checkbox'], True)


    # test parameter change API
    def test_parameterval_detail_patch(self):
        current_rev = self.workflow.revision

        request = self.factory.patch('/api/parameters/%d/' % self.numberID,
                                   {'number': '50.456' })
        force_authenticate(request, user=self.user)
        response = parameterval_detail(request, pk=self.numberID)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        request = self.factory.get('/api/parameters/%d/' % self.numberID)
        force_authenticate(request, user=self.user)
        response = parameterval_detail(request, pk=self.numberID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['number'], 50.456)

        # changing a parameter should bump the version
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.revision, current_rev+1)

