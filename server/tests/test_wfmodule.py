from django.test import TestCase
from server.views import wfmodule_detail, wfmodule_render
from rest_framework.test import APIRequestFactory
from rest_framework import status
from server.models import Module, WfModule, Workflow, ParameterSpec, ParameterVal
from server.dispatch import test_data_table
import pandas as pd
import json
import copy

class WfModuleTests(TestCase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        self.factory = APIRequestFactory()
        workflow1 = Workflow.objects.create(name='Workflow 1')
        workflow2 = Workflow.objects.create(name='Workflow 2')

        module1 = self.add_new_module('Module 1', 'testdata')
        self.pspec11 = ParameterSpec.objects.create(module=module1, type=ParameterSpec.NUMBER, def_number=3.14)
        self.pspec12 = ParameterSpec.objects.create(module=module1, type=ParameterSpec.STRING, def_string='foo')
        self.pspec13 = ParameterSpec.objects.create(module=module1, type=ParameterSpec.TEXT, def_text='bar')
        module2 = self.add_new_module('Module 2', 'NOP')
        module3 = self.add_new_module('Module 3', 'double_M_col')
        self.pspec31 = ParameterSpec.objects.create(module=module3, type=ParameterSpec.BUTTON)

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

    def add_new_module(self, name, dispatch):
        module = Module(name=name, dispatch=dispatch)
        module.save()
        return module

    # check that creating a wf_module correctly sets up new ParameterVals w/ defaults from ParameterSpec
    def test_default_parameters(self):
        self.wfmodule1.create_default_parameters()
        pval = ParameterVal.objects.get(parameter_spec=self.pspec11, wf_module=self.wfmodule1)
        self.assertEqual(pval.number, 3.14)

        pval = ParameterVal.objects.get(parameter_spec=self.pspec12, wf_module=self.wfmodule1)
        self.assertEqual(pval.string, 'foo')

        pval = ParameterVal.objects.get(parameter_spec=self.pspec13, wf_module=self.wfmodule1)
        self.assertEqual(pval.text, 'bar')

        # button has no value, so just checking existence here
        self.wfmodule3.create_default_parameters()
        pval = ParameterVal.objects.get(parameter_spec=self.pspec31, wf_module=self.wfmodule3)


    # TODO test parameter values returned from this call
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
        self.assertEqual(response.data['status'], WfModule.READY)
        self.assertEqual(response.data['error_msg'], '')
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