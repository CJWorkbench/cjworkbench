from django.test import TestCase
import json
import pandas as pd
import io
from server.views.WfModule import wfmodule_detail, wfmodule_render, wfmodule_dataversion, make_render_json
from rest_framework.test import APIRequestFactory
from rest_framework import status
from server.models import Module, ModuleVersion, WfModule, Workflow, ParameterSpec, ParameterVal
from rest_framework.test import force_authenticate
from server.tests.utils import *
from server.tests.test_wfmodule import WfModuleTestsBase
from operator import itemgetter

class WfModuleTests(LoggedInTestCase, WfModuleTestsBase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(WfModuleTests, self).setUp()  # log in
        self.createTestWorkflow()
        self.factory = APIRequestFactory()

    # TODO test parameter values returned from this call
    def test_wf_module_detail_get(self):
        # Also tests [Workflow, Module, WfModule].get
        workflow = Workflow.objects.get(name='Workflow 1')
        module_id = Module.objects.get(name='Module 1').id
        module_version = ModuleVersion.objects.get(module=Module.objects.get(name='Module 1'))
        wf_module = WfModule.objects.get(workflow_id=workflow.id, module_version=module_version)
        wf_module_versions = {
            'versions': wf_module.list_fetched_data_versions(),
            'selected': wf_module.get_fetched_data_version()
        }

        response = self.client.get('/api/wfmodules/%d/' % wf_module.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], wf_module.id)
        self.assertEqual(response.data['workflow'], workflow.id)
        self.assertEqual(response.data['notes'], wf_module.notes)
        self.assertEqual(response.data['module_version']['module']['id'], module_id)
        self.assertEqual(response.data['status'], wf_module.status)
        self.assertEqual(response.data['error_msg'], wf_module.error_msg)
        self.assertEqual(response.data['is_collapsed'], wf_module.is_collapsed)
        self.assertEqual(response.data['auto_update_data'], wf_module.auto_update_data)
        self.assertEqual(response.data['last_update_check'], wf_module.last_update_check)
        self.assertEqual(response.data['update_interval'], 1)       # defaults here to avoid time unit conversion
        self.assertEqual(response.data['update_units'], 'days')
        self.assertEqual(response.data['notifications'], wf_module.notifications)
        self.assertEqual(response.data['notification_count'], wf_module.notification_set.count())
        self.assertEqual(response.data['versions'], wf_module_versions)
        self.assertEqual(response.data['html_output'], wf_module.module_version.html_output)

        response = self.client.get('/api/wfmodules/%d/' % 10000)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_missing_module(self):
        # If the WfModule references a Module that does not exist, we should get a placeholder
        workflow = add_new_workflow('Missing module')
        wfm = add_new_wf_module(workflow, None, 0)
        response = self.client.get('/api/wfmodules/%d/' % wfm.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['module_version']['module']['name'], 'Missing module')
        self.assertEqual(response.data['module_version']['module']['loads_data'], False)

        response = self.client.get('/api/wfmodules/%d/render' % wfm.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        empty_table = make_render_json(pd.DataFrame())
        self.assertEqual(response.content.decode('utf-8'), empty_table)


    # this constrains the output API format, detects changes that would break client code
    def test_make_render_json(self):
        # test our basic test data
        output = make_render_json(self.test_table)
        self.assertTrue(isinstance(output,str))
        d1 = json.loads(output)
        d2 = {
            'total_rows': 4,
            'start_row': 0,
            'end_row': 4,
            'columns': ['Class', 'M', 'F'],
            'rows': [
                { 'Class': 'math', 'F': 12, 'M': 10.0},
                { 'Class': 'english', 'F': 7, 'M': None},
                { 'Class': 'history', 'F': 13, 'M': 11.0},
                { 'Class': 'economics', 'F': 20, 'M': 20.0}
            ],
            'column_types': [
                'String',
                'Number',
                'Number'
            ]
        }
        self.assertEqual(d1, d2)

        # Test some json conversion gotchas we encountered during development

        # simple test case where Pandas produces int64 column type, and json conversion throws ValueError
        # see https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257
        int64csv = 'A,B,C,D\n1,2,3,4'
        int64table = pd.read_csv(io.StringIO(int64csv), header=0)
        output = make_render_json(int64table)

        # When no header row, Pandas uses int64s as column names, and json.dumps(list(table)) throws ValueError
        int64table = pd.read_csv(io.StringIO(int64csv), header=None)
        output = make_render_json(int64table)


    def test_wf_module_render_get(self):
        # First module: creates test data
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # second module: NOP
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # Third module: doubles M column
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        double_test_data = self.test_table.copy()
        double_test_data['M'] *= 2
        double_test_data = make_render_json(double_test_data)
        self.assertEqual(response.content.decode('utf-8'), double_test_data)

        # Now test retrieving specified rows only
        response = self.client.get('/api/wfmodules/%d/render?startrow=1' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, startrow=1)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        response = self.client.get('/api/wfmodules/%d/render?startrow=1&endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, startrow=1, endrow=3)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        response = self.client.get('/api/wfmodules/%d/render?endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, endrow=3)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # index out of bounds should clip
        response = self.client.get('/api/wfmodules/%d/render?startrow=-1&endrow=500' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # index not a number -> bad request
        response = self.client.get('/api/wfmodules/%d/render?startrow=0&endrow=frog' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    # can we take one out?
    def test_wf_module_delete(self):
        # add a new one to delete; don't mess with other tests
        wfmodule4 = add_new_wf_module(self.workflow1, self.module2_version, 3)
        self.workflow1.selected_wf_module = wfmodule4.id

        response = self.client.delete('/api/wfmodules/%d' % wfmodule4.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WfModule.objects.filter(workflow=self.workflow1, pk=wfmodule4.id).exists())  # must really be gone

        # also check that deleting the selected module nullifies workflow.selected_wf_module
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.selected_wf_module, None)

    # /input is just a /render on the previous module
    def test_wf_module_input(self):
        # First module: no prior input, should be empty result
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(pd.DataFrame())
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # Second module: input should be test data produced by first module
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # Third module: should be same as second, as second module is NOP
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

    # tests for the /histogram API
    def test_wf_module_histogram(self):
        # The column name for histogram counts, to prevent name conflicts
        INTERNAL_COUNT_COLNAME = '__internal_count_column__'

        # First module: no prior input, should be empty result
        response = self.client.get('/api/wfmodules/%d/histogram/Class' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(pd.DataFrame())
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # Second module: histogram should be count 1 for each column
        response = self.client.get('/api/wfmodules/%d/histogram/Class' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data = self.test_table.groupby('Class').size().reset_index()
        test_data.columns = ['Class', INTERNAL_COUNT_COLNAME]
        test_data = test_data.sort_values(by=[INTERNAL_COUNT_COLNAME, 'Class'], ascending=[False, True])
        test_data_json = make_render_json(test_data)
        self.assertEqual(response.content.decode('utf-8'), test_data_json)

        # Test for non-existent column; should return a 204 code
        response = self.client.get('/api/wfmodules/%d/histogram/O' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    # tests for the /columns API
    def test_wf_module_columns(self):
        # We only need to check for one module since the output is pretty much the same
        # Dates are not tested here because the test WF cannot be fed date data
        response = self.client.get('/api/wfmodules/%d/columns' % self.wfmodule1.id)
        ref_columns = sorted([
            {"name": "Class", "type": "String"},
            {"name": "M", "type": "Number"},
            {"name": "F", "type": "Number"}
        ], key=itemgetter("name"))
        returned_columns = sorted(json.loads(response.content.decode('utf-8')), key=itemgetter("name"))
        self.assertEqual(returned_columns, ref_columns)


    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        firstver = self.wfmodule1.store_fetched_table(mock_csv_table)
        self.wfmodule1.set_fetched_data_version(firstver)
        secondver = self.wfmodule1.store_fetched_table(mock_csv_table2)

        # retrieve version list through the API
        response = self.client.get('/api/wfmodules/%d/dataversion' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        versiondata = {
            "versions": [
                [secondver.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), False],
                [firstver.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), False]
            ],
            "selected": firstver.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        responsedata = json.loads(response.content.decode('UTF-8'))
        self.assertEqual(responsedata, versiondata)

        # set the version back to latest through API.
        # using factory.patch as trouble getting client.patch to work (400 -- authentication?)
        # More or less the same thing, but does skip urls.py
        request = self.factory.patch('/api/wfmodules/%d/dataversion' % self.wfmodule1.id,
                                     {'selected': secondver.strftime("%Y-%m-%dT%H:%M:%S.%fZ")})
        force_authenticate(request, user=self.user)
        response = wfmodule_dataversion(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.wfmodule1.refresh_from_db()
        self.assertEqual(self.wfmodule1.get_fetched_data_version(), secondver)


    # test Wf Module Notes change API
    def test_wf_module_notes_post(self):
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                     {'notes': 'wow such doge'})
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'wow such doge')

        # Test for error on missing notes field (and no other patachable fields)
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                     {'notnotes': 'forthcoming error'})
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test set/get update interval
    def test_wf_module_update_settings(self):
        settings = {'auto_update_data': True,
                    'update_interval': 5,
                    'update_units': 'weeks'}

        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, settings)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new values back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['auto_update_data'], True)
        self.assertEqual(response.data['update_interval'], 5)
        self.assertEqual(response.data['update_units'], 'weeks')

        # Now check for error checking! As usual, this is most of the work
        missing_units_key = {'auto_update_data': True, 'update_interval': 1000}
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, missing_units_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

        missing_interval_key = {'auto_update_data': True, 'update_units': 'days'}
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, missing_interval_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

        bad_units_key = {'auto_update_data': True, 'update_interval': 66, 'update_units': 'pajama'}
        request = self.factory.patch('/api/wfmodules/%d' % self.wfmodule1.id, bad_units_key)
        force_authenticate(request, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)
