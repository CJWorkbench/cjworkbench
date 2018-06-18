from collections import namedtuple
from unittest.mock import patch
from allauth.account.utils import user_display
from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate
from server.serializers import WfModuleSerializer
from server.tests.utils import *
from server.views import workflow_list, workflow_addmodule, workflow_detail, embed


FakeSession = namedtuple('FakeSession', [ 'session_key' ])


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


    def _augment_request(self, request, user: User,
                         session_key: str) -> None:
        if user:
            force_authenticate(request, user=user)
        request.session = FakeSession(session_key)


    def _build_delete(self, *args, user: User=None, session_key: str='a-key',
                     **kwargs):
        request = self.factory.delete(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request


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


    def _build_post(self, *args, user: User=None, session_key: str='a-key',
                    **kwargs):
        request = self.factory.post(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request


    def _build_put(self, *args, user: User=None, session_key: str='a-key',
                   **kwargs):
        request = self.factory.put(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request


    def workflow_view(self):
        # View own non-public workflow
        response = self.client.get('/workflows/%d/' % self.workflow1.id)  # need trailing slash or 301
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 404 with bad id
        response = self.client.get('/workflows/%d/' % 999999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # View someone else's public workflow
        self.assertTrue(self.other_workflow_public.public)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        # 404 viewing someone else' private workflow
        self.assertFalse(self.workflow1.public)
        self.client.force_login(self.otheruser)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_workflow_init_state(self):
        # checks to make sure the right initial data is embedded in the HTML (username etc.)
        with patch.dict('os.environ', { 'CJW_INTERCOM_APP_ID':'myIntercomId', 'CJW_GOOGLE_ANALYTICS':'myGaId'}):

            # create an Edit Cells module so we can check that its ID is returned correctly
            edit_cells_module_id = add_new_module_version('Edit Cells', id_name='editcells').module_id

            response = self.client.get('/workflows/%d/' % self.workflow1.id)  # need trailing slash or 301
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertContains(response, '"loggedInUser"')
            self.assertContains(response, user_display(self.user))
            self.assertContains(response, self.user.email)

            self.assertContains(response, '"editCellsModuleId": ' + str(edit_cells_module_id))
            self.assertContains(response, '"workflow"')
            self.assertContains(response, '"modules"')

            self.assertContains(response, 'myIntercomId')
            self.assertContains(response, 'myGaId')


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

        request = self._build_get('/api/workflows/', user=self.user)
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
        request = self._build_post('/api/workflows/', user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), start_count+1)
        self.assertEqual(Workflow.objects.filter(name='New Workflow').count(), 1)


    def test_workflow_addmodule_put(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 0)

        module1 = Module.objects.get(name='Module 1')
        module2 = Module.objects.get(name='Module 2')
        module3 = Module.objects.get(name='Module 3')

        # add to empty stack
        request = self._build_put('/api/workflows/%d/addmodule/' % pk_workflow,
                                  {'moduleId': module1.id, 'insertBefore': 0},
                                  user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 1)
        wfm1 = WfModule.objects.filter(module_version__module=module1.id).first()
        self.assertEqual(response.data['id'], wfm1.id)
        # we should get a full serialization back, same as /wfmodules/xx call
        serializer = WfModuleSerializer(wfm1)
        # addmodule serialization should also return insert_before property
        return_data = serializer.data
        return_data['insert_before'] = '0'
        self.assertEqual(response.data, return_data)

        # insert before first module
        request = self._build_put('/api/workflows/%d/addmodule/' % pk_workflow,
                                  {'moduleId': module2.id, 'insertBefore': 0},
                                  user=self.user)
        response = workflow_addmodule(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 2)
        wfm2 = WfModule.objects.filter(module_version__module=module2.id).first()
        self.assertEqual(response.data['id'], wfm2.id)

        # insert before second module
        request = self._build_put('/api/workflows/%d/addmodule/' % pk_workflow,
                                  {'moduleId': module3.id, 'insertBefore': 1},
                                  user=self.user)
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
        request = self._build_put('/api/workflows/%d/addmodule/' % 10000,
                                  {'moduleId': module1.id, 'insertBefore': 0},
                                  user=self.user)
        response = workflow_addmodule(request, pk=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # bad module id
        request = self._build_put('/api/workflows/%d/addmodule/' % Workflow.objects.get(name='Workflow 1').id,
                                  {'moduleId': 10000, 'insertBefore': 0},
                                  user=self.user)
        response = workflow_addmodule(request, pk=Workflow.objects.get(name='Workflow 1').id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workflow_detail_get(self):
        pk_workflow = self.workflow1.id
        request = self._build_get('/api/workflows/%d/' % pk_workflow,
                                  user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Workflow 1')
        self.assertEqual(response.data['public'], False)

        # bad ID should give 404
        request = self._build_get('/api/workflows/%d/' % 10000,
                                  user=self.user)
        response = workflow_detail(request, pk = 10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # not authenticated should give 403
        request = self._build_get('/api/workflows/%d/' % pk_workflow,
                                  user=AnonymousUser())
        response = workflow_detail(request, pk = pk_workflow)
        self.assertEqual(response.status_code, 403)

        # someone else's public workflow should be gettable
        request = self._build_get('/api/workflows/%d/' % self.other_workflow_public.id,
                                  user=self.user)
        response = workflow_detail(request, pk = self.other_workflow_public.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Other workflow public')

        # someone else's private workflow should 403
        request = self._build_get('/api/workflows/%d/' % self.other_workflow_private.id,
                                  user=self.user)
        response = workflow_detail(request, pk=self.other_workflow_private.id)
        self.assertEqual(response.status_code, 403)


    def test_email_leakage(self):
        # We user email as display name if the user has not set first,last
        # But don't ever give this out for a public workflow, either through page or API
        request = self._build_get('/workflows/%d/' % self.other_workflow_public.id,
                                  user=None)
        response = workflow_detail(request, pk=self.other_workflow_public.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, self.otheruser.email)

        request = self._build_get('/api/workflows/%d/' % self.other_workflow_public.id,
                                  user=self.user)
        response = workflow_detail(request, pk = self.other_workflow_public.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertNotContains(response, self.otheruser.email)


    def test_workflow_reorder_modules(self):
        wfm1 = add_new_wf_module(self.workflow1, self.module_version1, 0)
        wfm2 = add_new_wf_module(self.workflow1, self.module_version1, 1)
        wfm3 = add_new_wf_module(self.workflow1, self.module_version1, 2)

        # your basic reordering
        request = self._build_patch('/api/workflows/%d/' % self.workflow1.id,
                                    data=[{'id': wfm1.id, 'order': 2},
                                          {'id': wfm2.id, 'order': 0},
                                          {'id': wfm3.id, 'order': 1}],
                                    format='json',
                                    user=self.user)
        response = workflow_detail(request, pk = self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(WfModule.objects.order_by('order').values_list('id', flat=True)),
                         [wfm2.id, wfm3.id, wfm1.id])

        # bad data should generate a 400 error
        # (we don't test every possible failure case, ReorderModulesCommand tests does that)
        request = self._build_patch('/api/workflows/%d/' % self.workflow1.id,
                                    data=[{'problem':'bad data'}],
                                    format='json',
                                    user=self.user)
        response = workflow_detail(request, pk = self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_workflow_detail_delete(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self._build_delete('/api/workflows/%d/' % pk_workflow,
                                     user=self.user)
        response = workflow_detail(request, pk = pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name='Workflow 1').count(), 0)


    def test_workflow_title_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.name, 'Workflow 1')
        pk_workflow = workflow.id
        request = self._build_post('/api/workflows/%d' % pk_workflow,
                                   {'newName': 'Billy Bob Thornton'},
                                   user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, 'Billy Bob Thornton')


    def test_workflow_public_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.public, False)
        pk_workflow = workflow.id
        request = self._build_post('/api/workflows/%d' % pk_workflow,
                                   {'public': True}, user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, True)


    def test_workflow_selected_wf_module_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.selected_wf_module, None)
        pk_workflow = workflow.id
        request = self._build_post('/api/workflows/%d' % pk_workflow,
                                   {'selected_wf_module': 808},
                                   user=self.user)
        response = workflow_detail(request, pk=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_wf_module, 808)
