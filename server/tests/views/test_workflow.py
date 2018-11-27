import asyncio
from collections import namedtuple
import json
from unittest.mock import patch
from allauth.account.utils import user_display
from django.contrib.auth.models import AnonymousUser
from django.http.response import Http404
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate
from server.models import Module, ModuleVersion, User, WfModule, Workflow
from server.models.commands import InitWorkflowCommand
from server.tests.utils import LoggedInTestCase, add_new_module_version, \
        add_new_wf_module, load_module_version
from server.views import workflow_list, AddModule, workflow_detail, \
        render_workflow, render_workflows, load_update_table_module_ids


FakeSession = namedtuple('FakeSession', ['session_key'])


async def async_noop(*args, **kwargs):
    pass


future_none = asyncio.Future()
future_none.set_result(None)


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class WorkflowViewTests(LoggedInTestCase):
    def setUp(self):
        super(WorkflowViewTests, self).setUp()  # log in

        self.log_patcher = patch('server.utils.log_user_event')
        self.log_patch = self.log_patcher.start()

        self.factory = APIRequestFactory()
        self.workflow1 = Workflow.objects.create(name='Workflow 1', owner=self.user)
        self.module_version1 = add_new_module_version('Module 1')

        # Add another user, with one public and one private workflow
        self.otheruser = User.objects.create(username='user2',
                                             email='user2@users.com',
                                             password='password')
        self.other_workflow_private = Workflow.objects.create(
            name="Other workflow private",
            owner=self.otheruser
        )
        self.other_workflow_public = Workflow.objects.create(
            name="Other workflow public",
            owner=self.otheruser,
            public=True
        )

    def tearDown(self):
        self.log_patcher.stop()
        super().tearDown()

    def _augment_request(self, request, user: User, session_key: str) -> None:
        if user:
            force_authenticate(request, user=user)
        request.session = FakeSession(session_key)
        request.user = user

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

    # --- Workflow list ---
    def test_workflow_list_get(self):
        # set dates to test reverse chron ordering
        self.workflow1.creation_date = "2010-10-20 1:23Z"
        self.workflow1.save()
        self.workflow2 = Workflow.objects.create(
            name='Workflow 2',
            owner=self.user,
            creation_date='2015-09-18 2:34Z'
        )

        request = self._build_get('/api/workflows/', user=self.user)
        response = render_workflows(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data['initState']['workflows']
        # should not pick up other user's workflows, even public ones
        self.assertEqual(len(workflows['owned']) + len(workflows['shared']) + len(workflows['templates']), 2)

        self.assertEqual(workflows['owned'][0]['name'], 'Workflow 2')
        self.assertEqual(workflows['owned'][0]['id'], self.workflow2.id)
        self.assertEqual(workflows['owned'][0]['public'], self.workflow1.public)
        self.assertEqual(workflows['owned'][0]['read_only'], False)  # user is owner
        self.assertEqual(workflows['owned'][0]['is_owner'], True)  # user is owner
        self.assertIsNotNone(workflows['owned'][0]['last_update'])
        self.assertEqual(workflows['owned'][0]['owner_name'], user_display(self.workflow2.owner))

        self.assertEqual(workflows['owned'][1]['name'], 'Workflow 1')
        self.assertEqual(workflows['owned'][1]['id'], self.workflow1.id)

    def test_workflow_list_include_example_in_all_users_workflow_lists(self):
        self.other_workflow_public.example = True
        self.other_workflow_public.in_all_users_workflow_lists = True
        self.other_workflow_public.save()
        self.workflow2 = Workflow.objects.create(owner=self.user)

        request = self._build_get('/api/workflows/', user=self.user)
        response = render_workflows(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data['initState']['workflows']
        self.assertEqual(len(workflows['owned']), 2)
        self.assertEqual(len(workflows['templates']), 1)

    def test_workflow_list_exclude_example_not_in_all_users_lists(self):
        self.other_workflow_public.example = True
        self.other_workflow_public.in_all_users_workflow_lists = False
        self.other_workflow_public.save()
        self.workflow2 = Workflow.objects.create(owner=self.user)

        request = self._build_get('/api/workflows/', user=self.user)
        response = render_workflows(request)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        workflows = response.context_data['initState']['workflows']
        self.assertEqual(len(workflows['owned']), 2)
        self.assertEqual(len(workflows['templates']), 0)

    def test_workflow_list_exclude_lesson(self):
        self.workflow1.lesson_slug = 'some-lesson'
        self.workflow1.save()
        self.workflow2 = Workflow.objects.create(owner=self.user)

        request = self._build_get('/api/workflows/', user=self.user)
        response = render_workflows(request)
        workflows = response.context_data['initState']['workflows']
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(workflows['owned']), 1)

    def test_workflow_list_post(self):
        start_count = Workflow.objects.count()
        request = self._build_post('/api/workflows/', user=self.user)
        response = workflow_list(request)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Workflow.objects.count(), start_count+1)
        self.assertEqual(Workflow.objects.filter(name='New Workflow').count(), 1)

    # --- Workflow ---
    # This is the HTTP response, as opposed to the API
    def test_workflow_view(self):
        # View own non-public workflow
        self.client.force_login(self.user)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)  # need trailing slash or 301
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('server.rabbitmq.queue_render')
    def test_workflow_view_triggers_render(self, queue_render):
        queue_render.return_value = future_none
        delta = InitWorkflowCommand.create(self.workflow1)
        self.workflow1.last_delta_id = delta.id
        self.workflow1.save(update_fields=['last_delta_id'])
        wf_module = self.workflow1.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id,
            cached_render_result_delta_id=-1
        )
        self.client.force_login(self.user)
        self.client.get('/workflows/%d/' % self.workflow1.id)
        queue_render.assert_called_with(self.workflow1.id, delta.id)

    @patch('server.rabbitmq.queue_render')
    def test_workflow_view_triggers_render_if_no_cache(self, queue_render):
        queue_render.return_value = future_none
        delta = InitWorkflowCommand.create(self.workflow1)
        self.workflow1.last_delta_id = delta.id
        self.workflow1.save(update_fields=['last_delta_id'])
        wf_module = self.workflow1.wf_modules.create(
            order=0,
            last_relevant_delta_id=delta.id,
            cached_render_result_delta_id=None
        )
        self.client.force_login(self.user)
        self.client.get('/workflows/%d/' % self.workflow1.id)
        queue_render.assert_called_with(self.workflow1.id, delta.id)

    def test_workflow_view_missing_404(self):
        # 404 with bad id
        self.client.force_login(self.user)
        response = self.client.get('/workflows/%d/' % 999999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_view_shared(self):
        # View someone else's public workflow
        self.client.force_login(self.user)
        self.assertTrue(self.other_workflow_public.public)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_workflow_view_shared(self):
        # View someone else's public workflow
        self.client.force_login(self.user)
        self.assertTrue(self.other_workflow_public.public)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)

    def test_workflow_view_unauthorized_403(self):
        # 403 viewing someone else' private workflow (don't 404 as sometimes
        # users try to share workflows by sharing the URL without first making
        # them public, and we need to help them debug that case)
        self.client.force_login(self.otheruser)
        response = self.client.get('/workflows/%d/' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_workflow_init_state(self):
        # checks to make sure the right initial data is embedded in the HTML (username etc.)
        with patch.dict('os.environ', { 'CJW_INTERCOM_APP_ID':'myIntercomId', 'CJW_GOOGLE_ANALYTICS':'myGaId'}):

            # create an Edit Cells module so we can check that its ID is returned correctly
            edit_cells_module_id = add_new_module_version('Edit Cells', id_name='editcells').module_id
            load_update_table_module_ids.cache_clear()

            response = self.client.get('/workflows/%d/' % self.workflow1.id)  # need trailing slash or 301
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertContains(response, '"loggedInUser"')
            self.assertContains(response, user_display(self.user))
            self.assertContains(response, self.user.email)

            self.assertContains(response, '"editcells": ' + str(edit_cells_module_id))
            self.assertContains(response, '"workflow"')
            self.assertContains(response, '"modules"')
            self.assertNotContains(response, '"reorder-column"')

            self.assertContains(response, 'myIntercomId')
            self.assertContains(response, 'myGaId')

    def test_workflow_acl_reader_reads_but_does_not_write(self):
        # Looking at an example workflow as an anonymous user should create a new workflow
        self.workflow1.acl.create(email='user2@users.com', can_edit=False)
        self.client.force_login(self.otheruser)

        # GET: works
        response = self.client.get(f'/api/workflows/{self.workflow1.id}/')
        self.assertEqual(response.status_code, 200)

        # POST: does not work
        response = self.client.post(f'/api/workflows/{self.workflow1.id}/',
                                    data='{"newName":"X"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_workflow_acl_writer_reads_and_writes(self):
        # Looking at an example workflow as an anonymous user should create a new workflow
        self.workflow1.acl.create(email='user2@users.com', can_edit=True)
        self.client.force_login(self.otheruser)

        # GET: works
        response = self.client.get(f'/api/workflows/{self.workflow1.id}/')
        self.assertEqual(response.status_code, 200)

        # POST: works
        response = self.client.post(f'/api/workflows/{self.workflow1.id}/',
                                    data='{"newName":"X"}',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 204)

    def test_workflow_anonymous_user(self):
        # Looking at an example workflow as an anonymous user should create a new workflow
        num_workflows = Workflow.objects.count()

        self.other_workflow_public.example = True
        self.other_workflow_public.save()

        # Also ensure the anonymous users can't access the Python module; first we need to load it
        load_module_version('pythoncode')

        request = self._build_get('/api/workflows/%d/' % self.other_workflow_public.id, user=AnonymousUser())
        response = render_workflow(request, workflow_id=self.other_workflow_public.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Workflow.objects.count(), num_workflows + 1)  # should have duplicated the  wf with this API call

        # Ensure the anonymous users can't access the Python module
        self.assertNotContains(response, '"pythoncode"')

    def test_workflow_duplicate_view(self):
        old_ids = [w.id for w in Workflow.objects.all()] # list of all current workflow ids
        response = self.client.post('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = json.loads(response.content)
        self.assertFalse(data['id'] in old_ids) # created at entirely new id
        self.assertEqual(data['name'], 'Copy of Workflow 1')
        self.assertTrue(Workflow.objects.filter(pk=data['id']).exists())

    def test_workflow_duplicate_missing_gives_404(self):
        # Ensure 404 with bad id
        response = self.client.post('/api/workflows/99999/duplicate')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_workflow_duplicate_restricted_gives_403(self):
        # Ensure 403 when another user tries to clone private workflow
        self.assertFalse(self.workflow1.public)
        self.client.force_login(self.otheruser)
        response = self.client.post('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_workflow_duplicate_public(self):
        self.workflow1.public = True
        self.workflow1.save()
        response = self.client.post('/api/workflows/%d/duplicate' % self.workflow1.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_workflow_detail_get(self):
        # Should be able to get your own workflow
        pk_workflow = self.workflow1.id
        request = self._build_get('/api/workflows/%d/' % pk_workflow,
                                  user=self.user)
        response = workflow_detail(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['workflow']['name'], 'Workflow 1')
        self.assertEqual(response.data['workflow']['public'], False)

        # bad ID should give 404
        request = self._build_get('/api/workflows/%d/' % 10000,
                                  user=self.user)
        response = workflow_detail(request, workflow_id=10000)
        self.assertIs(response.status_code, status.HTTP_404_NOT_FOUND)

        # someone else's public workflow should be gettable
        request = self._build_get('/api/workflows/%d/' % self.other_workflow_public.id,
                                  user=self.user)
        response = workflow_detail(request, workflow_id=self.other_workflow_public.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['workflow']['name'], 'Other workflow public')

        # not authenticated should give 403 (not 404, because users try to
        # share their URLs without setting them public first and we need to
        # help them debug that case)
        request = self._build_get('/api/workflows/%d/' % pk_workflow,
                                  user=AnonymousUser())
        response = workflow_detail(request, workflow_id=pk_workflow)
        self.assertEqual(response.status_code, 403)

        # similarly, someone else's private workflow should 403
        request = self._build_get('/api/workflows/%d/' % self.other_workflow_private.id,
                                  user=self.user)
        response = workflow_detail(request, workflow_id=self.other_workflow_private.id)
        self.assertEqual(response.status_code, 403)

    # --- Writing to workflows ---
    def test_workflow_addmodule_post(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 0)

        module1 = Module.objects.get(name='Module 1')

        # add to empty stack
        request = self._build_post('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': module1.id, 'index': 0},
                                   format='json', user=self.user)
        response = AddModule().post(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WfModule.objects.filter(workflow=pk_workflow).count(), 1)
        wfm1 = WfModule.objects.filter(module_version__module=module1.id).first()
        response_data = json.loads(response.content)
        self.assertEqual(response_data['wfModule']['id'], wfm1.id)
        self.assertEqual(response_data['wfModule']['module_version']['module'],
                         module1.id)
        self.assertEqual(response_data['index'], 0)

    def test_workflow_addmodule_post_bad_workflow_id(self):
        module1 = Module.objects.get(name='Module 1')
        request = self._build_post('/api/workflows/%d/addmodule/' % 10000,
                                   {'moduleId': module1.id, 'index': 0},
                                   user=self.user)
        with self.assertRaises(Http404):
            response = AddModule().post(request, workflow_id=10000)
        self.assertEqual(WfModule.objects.count(), 0)

    def test_workflow_addmodule_post_bad_module_id(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self._build_post('/api/workflows/%d/addmodule/' % pk_workflow,
                                   {'moduleId': 10000, 'index': 0},
                                   user=self.user)
        response = AddModule().post(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(WfModule.objects.count(), 0)

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
        response = workflow_detail(request, workflow_id=self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(list(WfModule.objects.order_by('order').values_list('id', flat=True)),
                         [wfm2.id, wfm3.id, wfm1.id])

        # bad data should generate a 400 error
        # (we don't test every possible failure case, ReorderModulesCommand tests does that)
        request = self._build_patch('/api/workflows/%d/' % self.workflow1.id,
                                    data=[{'problem':'bad data'}],
                                    format='json',
                                    user=self.user)
        response = workflow_detail(request, workflow_id=self.workflow1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_workflow_detail_delete(self):
        pk_workflow = Workflow.objects.get(name='Workflow 1').id
        request = self._build_delete('/api/workflows/%d/' % pk_workflow,
                                     user=self.user)
        response = workflow_detail(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workflow.objects.filter(name='Workflow 1').count(), 0)

    def test_workflow_title_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.name, 'Workflow 1')
        pk_workflow = workflow.id
        request = self._build_post('/api/workflows/%d' % pk_workflow,
                                   {'newName': 'Billy Bob Thornton'},
                                   user=self.user)
        response = workflow_detail(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.name, 'Billy Bob Thornton')

    def test_workflow_public_post(self):
        workflow = Workflow.objects.get(name='Workflow 1')
        self.assertEqual(workflow.public, False)
        pk_workflow = workflow.id
        request = self._build_post('/api/workflows/%d' % pk_workflow,
                                   {'public': True}, user=self.user)
        response = workflow_detail(request, workflow_id=pk_workflow)
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
        response = workflow_detail(request, workflow_id=pk_workflow)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        workflow.refresh_from_db()
        self.assertEqual(workflow.selected_wf_module, 808)
