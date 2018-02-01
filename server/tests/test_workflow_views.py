from server.views import workflow_list, workflow_addmodule, workflow_detail
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from server.utils import *
from server.tests.utils import *
from account.utils import user_display
from unittest.mock import patch

class WorkflowViewTests(LoggedInTestCase):
    def setUp(self):
        super(WorkflowViewTests, self).setUp()  # log in
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

    def test_workflow_init_state(self):
        # checks to make sure the right initial data is embedded in the HTML (username etc.)
        with patch.dict('os.environ', { 'CJW_INTERCOM_APP_ID':'myappid'}):
            response = self.client.get('/workflows/%d/' % self.workflow1.id)  # need trailing slash or 301
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertContains(response, '"loggedInUser":')
            self.assertContains(response, user_display(self.user))
            self.assertContains(response, self.user.email)
            self.assertContains(response, '"intercomAppId":')
            self.assertContains(response, '"myappid"')


    def test_workflow_duplicate_view(self):
        old_ids = [w.id for w in Workflow.objects.all()] # list of all current workflow ids
        response = self.client.get('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_id = response.data['id']
        self.assertFalse(new_id in old_ids)         # created at entirely new id
        self.assertEqual(response.data['name'], 'Copy of ' + self.workflow1.name)
        new_wf = Workflow.objects.get(pk=new_id)    # will fail if no Workflow created

        # Ensure 404 with bad id
        response = self.client.get('/api/workflows/%d/duplicate' % 999999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Ensure 403 when another user tries to clone private workflow
        self.assertFalse(self.workflow1.public)
        self.client.force_login(self.otheruser)
        response = self.client.get('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # But another user can duplicate public workflow
        self.workflow1.public = True
        self.workflow1.save()
        response = self.client.get('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_workflow_list_get(self):
        # set dates to test reverse chron ordering
        self.workflow1.creation_date = "2010-10-20 1:23Z"
        self.workflow1.save()
        self.workflow2.creation_date = "2015-09-18 2:34Z"
        self.workflow2.save()

        request = self.factory.get('/api/workflows/')
        force_authenticate(request, user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # should not pick up other user's workflows, even public ones

        self.assertEqual(response.data[0]['name'], 'Workflow 2')
        self.assertEqual(response.data[0]['id'], self.workflow2.id)
        self.assertEqual(response.data[0]['public'], self.workflow1.public)
        self.assertEqual(response.data[0]['read_only'], False)  # if we can list it, it's ours and we can edit it
        self.assertIsNotNone(response.data[0]['last_update'])
        self.assertEqual(response.data[0]['owner_name'], user_display(self.workflow2.owner))

        self.assertEqual(response.data[1]['name'], 'Workflow 1')
        self.assertEqual(response.data[1]['id'], self.workflow1.id)


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
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 0)

        module1 = Module.objects.get(name='Module 1')
        module2 = Module.objects.get(name='Module 2')
        module3 = Module.objects.get(name='Module 3')

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': module1.id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 1)
        wfm1 = WfModule.objects.filter(module_version__module=module1.id).first()
        self.assertEqual(response.data['id'], wfm1.id)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': module2.id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 2)
        wfm2 = WfModule.objects.filter(module_version__module=module2.id).first()
        self.assertEqual(response.data['id'], wfm2.id)

        request = self.factory.put('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': module3.id,
                                    'insertBefore': 1})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 3)
        wfm3 = WfModule.objects.filter(module_version__module=module3.id).first()
        self.assertEqual(response.data['id'], wfm3.id)

        # check for correct insertion order
        self.assertEqual(list(WfModule.objects.values_list('module_version', flat=True)),
                         [ModuleVersion.objects.get(module=module2).id,
                          ModuleVersion.objects.get(module=module3).id,
                          ModuleVersion.objects.get(module=module1).id])

        # bad workflow id
        request = self.factory.put('/api/workflows/%d/addmodule/' % 10000,
                                   {'moduleId': module1.id,
                                    'insertBefore': 0})
        force_authenticate(request, user=self.user)
        response = workflow_addmodule(request, pk=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # bad module id
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
        self.assertEqual(response.data['public'], False)
        self.assertEqual(response.data['module_library_collapsed'], False)

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


    def test_email_leakage(self):
        # We user email as display name if the user has not set first,last
        # But don't ever give this out for a public workflow, either through page or API
        response = self.client.get('/workflows/%d/' % self.other_workflow_public.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, self.otheruser.email)

        request = self.factory.get('/api/workflows/%d/' % self.other_workflow_public.id)
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk = self.other_workflow_public.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, self.otheruser.email)


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


    def test_workflow_title_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.name, 'Workflow 1')
        pk_workflow = workflow.id
        request = self.factory.post('/api/workflows/%d' % pk_workflow,
                                   {'newName': 'Billy Bob Thornton'})
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, 'Billy Bob Thornton')


    def test_workflow_public_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.public, False)
        pk_workflow = workflow.id
        request = self.factory.post('/api/workflows/%d' % pk_workflow,
                                   {'public': True})
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, True)


    def test_workflow_library_collapse_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.module_library_collapsed, False)
        pk_workflow = workflow.id
        request = self.factory.post('/api/workflows/%d' % pk_workflow,
                                   {'module_library_collapsed': True})
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.module_library_collapsed, True)


    def test_workflow_selected_wf_module_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.selected_wf_module, None)
        pk_workflow = workflow.id
        request = self.factory.post('/api/workflows/%d' % pk_workflow,
                                   {'selected_wf_module': 808})
        force_authenticate(request, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_wf_module, 808)