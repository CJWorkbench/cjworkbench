from django.test import TestCase
from server.views import workflow_list, workflow_addmodule, workflow_detail, wfmodule_detail, wfmodule_render, module_list, parameterval_detail
from rest_framework.test import APIRequestFactory
from rest_framework import status
from server.models import ParameterVal, ParameterSpec, Module, WfModule, Workflow
from server.dispatch import test_data_table
import pandas as pd
import json

class WorkflowTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.add_new_workflow('Workflow 1')
        self.add_new_workflow('Workflow 2')
        self.add_new_module('Module 1')
        self.add_new_module('Module 2')
        self.add_new_module('Module 3')

    def add_new_workflow(self, name):
        workflow = Workflow(name=name)
        workflow.save()

    def add_new_module(self, name):
        module = Module(name=name)
        module.save()

    def test_workflow_list_get(self):
        request = self.factory.get('/api/workflows/')
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'Workflow 1')
        self.assertEqual(response.data[1]['name'], 'Workflow 2')

    def test_workflow_list_post(self):
        request = self.factory.post('/api/workflows/', {'name': 'Workflow 3'})
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), 3)
        self.assertEqual(Workflow.objects.filter(name='Workflow 3').count(), 1)

    def test_workflow_addmodule_put(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 2').id,
                                    'insertBefore': 0})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 3').id,
                                    'insertBefore': 1})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(list(WfModule.objects.values_list('module', flat=True)),
                         [Module.objects.get(name='Module 2').id,
                          Module.objects.get(name='Module 3').id,
                          Module.objects.get(name='Module 1').id])

        request = self.factory.put('/api/workflows/%d/addmodule/' % 10000,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        response = workflow_addmodule(request, pk=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        request = self.factory.put('/api/workflows/%d/addmodule/' % Workflow.objects.get(name='Workflow 1').id,
                                   {'moduleID': 10000,
                                    'insertBefore': 0})
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
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Workflow 1')
        request = self.factory.get('/api/workflows/%d/' % 10000)
        response = workflow_detail(request, pk = 10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_detail_patch(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 2').id,
                                    'insertBefore': 0})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleID': Module.objects.get(name='Module 3').id,
                                    'insertBefore': 1})
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.patch('/api/workflows/%d/' % pk_workflow, data=[{'id': 1, 'order': 1},
                                                                               {'id': 2, 'order': 2},
                                                                               {'id': 3, 'order': 3}], format='json')
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(WfModule.objects.values_list('id', flat=True)), [1, 2, 3])

    def test_workflow_detail_delete(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.delete('/api/workflows/%d/' % pk_workflow)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertEqual(Workflow.objects.filter(name='Workflow 1').count(), 0)



class WfModuleTests(TestCase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        self.factory = APIRequestFactory()
        workflow1 = Workflow(name='Workflow 1')
        workflow1.save()
        workflow2 = Workflow(name='Workflow 2')
        workflow2.save()
        module1 = self.add_new_module('Module 1', 'testdata')
        module2 = self.add_new_module('Module 2', 'NOP')
        module3 = self.add_new_module('Module 3', 'double_M_col')
        self.wfmodule1 = self.add_new_wfmodule(workflow1, module1, 1)
        self.wfmodule2 = self.add_new_wfmodule(workflow1, module2, 2)
        self.wfmodule3 = self.add_new_wfmodule(workflow1, module3, 3)
        self.add_new_wfmodule(workflow2, module1, 1)
        self.add_new_wfmodule(workflow2, module2, 2)
        self.add_new_wfmodule(workflow2, module3, 3)

    def add_new_wfmodule(self, workflow_aux, module_aux, order_aux):
        wf_module = WfModule(workflow=workflow_aux, module=module_aux, order=order_aux)
        wf_module.save()
        return wf_module

    def add_new_workflow(self, name):
        workflow = Workflow(name=name)
        workflow.save()

    def add_new_module(self, name, dispatch):
        module = Module(name=name, dispatch=dispatch)
        module.save()
        return module

    def test_wf_module_detail_get(self):
        # Also tests [Workflow, Module, WfModule].get
        workflow_id = Workflow.objects.get(name='Workflow 1').id
        module_id = Module.objects.get(name='Module 1').id
        pk_wf_module = WfModule.objects.get(workflow_id=workflow_id,
                                           module_id = module_id).id

        request = self.factory.get('/api/wfmodules/%d/' % pk_wf_module)
        response = wfmodule_detail(request, pk = pk_wf_module)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pk_wf_module)
        self.assertEqual(response.data['workflow']['id'], workflow_id)
        self.assertEqual(response.data['module']['id'], module_id)
        request = self.factory.get('/api/wfmodules/%d/' % 10000)
        response = wfmodule_detail(request, pk = 10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_wf_module_render_get(self):

        # First module: creates test data
        request = self.factory.get('/api/wfmodules/%d/render' % self.wfmodule1.id)
        response = wfmodule_render(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = json.dumps(test_data_table.to_dict(orient='list')).encode('UTF=8')
        self.assertEqual(response.content, test_data_json)

        # second module: NOP
        request = self.factory.get('/api/wfmodules/%d/render' % self.wfmodule2.id)
        response = wfmodule_render(request, pk=self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, test_data_json)

        # Third module: doubles M column
        request = self.factory.get('/api/wfmodules/%d/render' % self.wfmodule3.id)
        response = wfmodule_render(request, pk=self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        double_test_data = pd.DataFrame(test_data_table['Class'], test_data_table['M']*2, test_data_table['F'])
        double_test_data = json.dumps(double_test_data.to_dict(orient='list')).encode('UTF=8')
        self.assertEqual(response.content, double_test_data)


class ModuleTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.add_new_module('Module 1')
        self.add_new_module('Module 2')
        self.add_new_module('Module 3')

    def add_new_module(self, name):
        module = Module(name=name, internal_name=name+'_internal', dispatch=name+'_dispatch')
        module.save()

    def test_module_list_get(self):
        request = self.factory.get('/api/modules/')
        response = module_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Module 1')
        self.assertEqual(response.data[1]['name'], 'Module 2')
        self.assertEqual(response.data[2]['name'], 'Module 3')

class ParameterValTests(TestCase):
    def setUp(self):
        # Create a WfModule with one parameter of each type
        self.factory = APIRequestFactory()
        module = Module(name="TestModule")
        module.save()
        self.moduleID = module.id

        stringSpec = ParameterSpec(name="StringParam", module=module, type= ParameterSpec.STRING, def_string='foo', def_number=0, def_text='')
        stringSpec.save()
        stringVal = ParameterVal()
        numberSpec = ParameterSpec(name="NumberParam", module=module, type=ParameterSpec.NUMBER, def_string='', def_number=10.11, def_text='')
        numberSpec.save()
        textSpec = ParameterSpec(name="TextParam", module=module, type=ParameterSpec.TEXT, def_string='', def_number=0, def_text='bar')
        textSpec.save()

        self.workflow = Workflow.objects.create(name="Test Workflow")
        self.workflowID = self.workflow.id

        self.wfmodule = WfModule.objects.create(module=module, workflow=self.workflow, order=0)
        self.wfmoduleID = self.wfmodule.id

        # set non-default values for vals in order to reveal certain types of bugs
        stringVal = ParameterVal.objects.create(parameter_spec=stringSpec, wf_module=self.wfmodule, string='fooval')
        self.stringID = stringVal.id

        numberVal = ParameterVal.objects.create(parameter_spec=numberSpec, wf_module=self.wfmodule, number=10.11)
        self.numberID = numberVal.id

        textVal = ParameterVal.objects.create(parameter_spec=textSpec, wf_module=self.wfmodule, text='barval')
        self.textID = textVal.id

    # Value retrieval methods must return correct values and enforce type
    def test_parameter_get_values(self):
        s = self.wfmodule.get_param_string('StringParam')
        self.assertEqual(s, 'fooval')

        n = self.wfmodule.get_param_number('NumberParam')
        self.assertEqual(n, 10.11)

        t = self.wfmodule.get_param_text('TextParam')
        self.assertEqual(t, 'barval')

        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('NumberParam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_string('TextParam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_number('StringParam')
        with self.assertRaises(ValueError):
            self.wfmodule.get_param_text('StringParam')

    # Parameter API must return correct values
    def test_parameterval_detail_get(self):
        request = self.factory.get('/api/workflows/%d/' % self.workflowID)
        response = workflow_detail(request, pk = self.workflowID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Workflow')

        # workflow has correct wfmodule
        self.assertEqual(len(response.data['wf_modules']), 1)
        self.assertEqual(response.data['wf_modules'][0]['module']['id'], self.moduleID)

        # wfmodule has correct parameters
        self.assertEqual(len(response.data['wf_modules'][0]['parameter_vals']), 3)
        valIDs = [self.stringID, self.numberID, self.textID]
        param_vals = response.data['wf_modules'][0]['parameter_vals']
        responseIDs = [x['id'] for x in param_vals]
        self.assertCountEqual(responseIDs, valIDs)

        # parameters have correct types and values
        str_val = [p for p in param_vals if p['id']==self.stringID][0]
        self.assertEqual(str_val['parameter_spec']['name'], 'StringParam')
        self.assertEqual(str_val['parameter_spec']['type'], ParameterSpec.STRING)
        self.assertEqual(str_val['string'], 'fooval')

        num_val = [p for p in param_vals if p['id']==self.numberID][0]
        self.assertEqual(num_val['parameter_spec']['name'], 'NumberParam')
        self.assertEqual(num_val['parameter_spec']['type'], ParameterSpec.NUMBER)
        self.assertEqual(num_val['number'], 10.11)

        text_val = [p for p in param_vals if p['id']==self.textID][0]
        self.assertEqual(text_val['parameter_spec']['name'], 'TextParam')
        self.assertEqual(text_val['parameter_spec']['type'], ParameterSpec.TEXT)
        self.assertEqual(text_val['text'], 'barval')


    # test parameter change API
    def test_parameterval_detail_patch(self):
        current_rev = self.workflow.revision

        request = self.factory.patch('/api/parameters/%d/' % self.numberID,
                                   {'number': '50.456' })
        response = parameterval_detail(request, pk=self.numberID)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        request = self.factory.get('/api/parameters/%d/' % self.numberID)
        response = parameterval_detail(request, pk=self.numberID)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['number'], 50.456)

        # changing a parameter should bump the version
        self.workflow.refresh_from_db()
        self.assertEqual(self.workflow.revision, current_rev+1)

