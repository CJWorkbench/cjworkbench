from django.test import TestCase
from server.views import workflow_list, workflow_addmodule, workflow_detail, parameterval_detail
from server.views.WfModule import wfmodule_detail,wfmodule_render
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.models import ParameterVal, ParameterSpec, Module, WfModule, Workflow
from server.tests.utils import *
import pandas as pd
import json

class WorkflowTests(LoggedInTestCase):
    def setUp(self):
        super(WorkflowTests, self).setUp()  # log in
        self.factory = APIRequestFactory()
        self.workflow1 = add_new_workflow('Workflow 1')
        self.workflow2 = add_new_workflow('Workflow 2')
        self.module_version1 = add_new_module_version('Module 1')
        add_new_module_version('Module 2')
        add_new_module_version('Module 3')

        # Add another user, with one public and one private workflow
        self.otheruser = User.objects.create(username='user2', email='user2@users.com', password='password')
        self.other_workflow_private = Workflow.objects.create(name="Other workflow private", owner=self.otheruser)
        self.other_workflow_public = Workflow.objects.create(name="Other workflow public", owner=self.otheruser, public=True)

    def test_workflow_list_get(self):
        request = self.factory.get('/api/workflows/')
        force_authenticate(request, user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # should not pick up other user's workflows, even public ones
        self.assertEqual(response.data[0]['name'], 'Workflow 1')
        self.assertEqual(response.data[1]['name'], 'Workflow 2')

    def test_workflow_list_post(self):
        start_count = Workflow.objects.count()
        request = self.factory.post('/api/workflows/', {'name': 'Workflow 3'})
        force_authenticate(request, user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), start_count+1)
        self.assertEqual(Workflow.objects.filter(name='Workflow 3').count(), 1)

    def test_workflow_addmodule_put(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': Module.objects.get(name='Module 2').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': Module.objects.get(name='Module 3').id,
                                    'insertBefore': 1})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        module1 = Module.objects.get(name='Module 1')
        module2 = Module.objects.get(name='Module 2')
        module3 = Module.objects.get(name='Module 3')

        self.assertEqual(list(WfModule.objects.values_list('module_version', flat=True)),
                         [ModuleVersion.objects.get(module = module2).id,
                          ModuleVersion.objects.get(module=module3).id,
                          ModuleVersion.objects.get(module=module1).id])

        request = self.factory.put('/api/workflows/%d/addmodule/' % 10000,
                                   {'moduleId': Module.objects.get(name='Module 1').id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        request = self.factory.put('/api/workflows/%d/addmodule/' % Workflow.objects.get(name='Workflow 1').id,
                                   {'moduleId': 10000,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=Workflow.objects.get(name='Workflow 1').id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workflow_detail_get(self):
        pk_workflow = self.workflow1.id
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

        # not authenticated should also give 404 so we don't expose an attack surface
        request = self.factory.get('/api/workflows/%d/' % pk_workflow)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # someone else's public workflow should be gettable
        request = self.factory.get('/api/workflows/%d/' % self.other_workflow_public.id)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = self.other_workflow_public.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Other workflow public')

        # someone else's private workflow should 404
        request = self.factory.get('/api/workflows/%d/' % self.other_workflow_private.id)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=self.other_workflow_private.id)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_workflow_reorder_modules(self):
        wfm1 = add_new_wf_module(self.workflow1, self.module_version1, 0)
        wfm2 = add_new_wf_module(self.workflow1, self.module_version1, 1)
        wfm3 = add_new_wf_module(self.workflow1, self.module_version1, 2)

        # your basic reordering
        request = self.factory.patch('/api/workflows/%d/' % self.workflow1.id,
                                     data=[{'id': wfm1.id, 'order': 2},
                                           {'id': wfm2.id, 'order': 0},
                                           {'id': wfm3.id, 'order': 1}],
                                     format='json')
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(WfModule.objects.order_by('order').values_list('id', flat=True)),
                         [wfm2.id, wfm3.id, wfm1.id])

        # bad data should generate a 400 error
        # (we don't test every possible failure case, ReorderModulesCommand tests does that)
        request = self.factory.patch('/api/workflows/%d/' % self.workflow1.id,
                                     data=[{'problem':'bad data'}],
                                     format='json')
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workflow_detail_delete(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.delete('/api/workflows/%d/' % pk_workflow)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name='Workflow 1').count(), 0)


    # test Wf Module Notes change API
    def test_workflow_title_post(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self.factory.post('/api/workflows/%d' % pk_workflow,
                                   {'newName': 'Billy Bob Thornton'})
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        request = self.factory.get('/api/wfmodules/%d/' % pk_workflow,)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request,  pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Billy Bob Thornton')
