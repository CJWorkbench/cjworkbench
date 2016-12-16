from django.test import TestCase
from .views import workflow_list, workflow_addmodule, workflow_detail, wfmodule_detail, module_list
from rest_framework.test import APIRequestFactory
from rest_framework import status
from .models import ParameterVal, ParameterSpec, Module, WfModule, Workflow

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
    def setUp(self):
        self.factory = APIRequestFactory()
        workflow1 = Workflow(name='Workflow 1')
        workflow1.save()
        workflow2 = Workflow(name='Workflow 2')
        workflow2.save()
        module1 = Module(name='Module 1')
        module1.save()
        module2 = Module(name='Module 2')
        module2.save()
        module3 = Module(name='Module 3')
        module3.save()
        self.add_new_wfmodule(workflow1, module1, 1)
        self.add_new_wfmodule(workflow1, module2, 2)
        self.add_new_wfmodule(workflow1, module3, 3)
        self.add_new_wfmodule(workflow2, module1, 1)
        self.add_new_wfmodule(workflow2, module2, 2)
        self.add_new_wfmodule(workflow2, module3, 3)

    def add_new_wfmodule(self, workflow_aux, module_aux, order_aux):
        wf_module = WfModule(workflow=workflow_aux, module=module_aux, order=order_aux)
        wf_module.save()

    def add_new_workflow(self, name):
        workflow = Workflow(name=name)
        workflow.save()

    def add_new_module(self, name):
        module = Module(name=name)
        module.save()

    def test_wf_module_detail_get(self):
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

class ModuleTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.add_new_module('Module 1')
        self.add_new_module('Module 2')
        self.add_new_module('Module 3')

    def add_new_module(self, name):
        module = Module(name=name)
        module.save()

    def test_module_list_get(self):
        request = self.factory.get('/api/modules/')
        response = module_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Module 1')
        self.assertEqual(response.data[1]['name'], 'Module 2')
        self.assertEqual(response.data[2]['name'], 'Module 3')