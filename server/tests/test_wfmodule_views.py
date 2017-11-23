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

class WfModuleTests(LoggedInTestCase, WfModuleTestsBase):

    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(WfModuleTests, self).setUp()  # log in
        self.createTestWorkflow()
        self.factory = APIRequestFactory()

    # TODO test parameter values returned from this call
    def test_wf_module_detail_get(self):
        # Also tests [Workflow, Module, WfModule].get
        workflow_id = Workflow.objects.get(name='Workflow 1').id
        module_id = Module.objects.get(name='Module 1').id
        module_version = ModuleVersion.objects.get(module=Module.objects.get(name='Module 1'))
        pk_wf_module = WfModule.objects.get(workflow_id=workflow_id,
                                            module_version=module_version).id
        notes = WfModule.objects.get(workflow_id=workflow_id,
                                     module_version=module_version).notes

        response = self.client.get('/api/wfmodules/%d/' % pk_wf_module)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pk_wf_module)
        self.assertEqual(response.data['workflow'], workflow_id)
        self.assertEqual(response.data['notes'], notes)
        self.assertEqual(response.data['module_version']['module']['id'], module_id)
        self.assertEqual(response.data['status'], WfModule.READY)
        self.assertEqual(response.data['error_msg'], '')

        response = self.client.get('/api/wfmodules/%d/' % 10000)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # this constrains the output API format, detects changes that would break client code
    def test_make_render_json(self):
        # test our basic test data
        output = make_render_json(self.test_table)
        d1 = json.loads(str(output, 'utf-8'))
        d2 = {
            'total_rows': 4,
            'start_row': 0,
            'end_row': 4,
            'columns': ['Class', 'M', 'F'],
            'rows': [
                {'Class': 'math', 'F': 12, 'M': 10.0},
                {'Class': 'english', 'F': 7, 'M': None},
                {'Class': 'history', 'F': 13, 'M': 11.0},
                {'Class': 'economics', 'F': 20, 'M': 20.0}
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
        self.assertEqual(response.content, test_data_json)

        # second module: NOP
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, test_data_json)

        # Third module: doubles M column
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        double_test_data = self.test_table.copy()
        double_test_data['M'] *= 2
        double_test_data = make_render_json(double_test_data)
        self.assertEqual(response.content, double_test_data)

        # Now test retrieving specified rows only
        response = self.client.get('/api/wfmodules/%d/render?startrow=1' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, startrow=1)
        self.assertEqual(response.content, test_data_json)

        response = self.client.get('/api/wfmodules/%d/render?startrow=1&endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, startrow=1, endrow=3)
        self.assertEqual(response.content, test_data_json)

        response = self.client.get('/api/wfmodules/%d/render?endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table, endrow=3)
        self.assertEqual(response.content, test_data_json)

        # index out of bounds should clip
        response = self.client.get('/api/wfmodules/%d/render?startrow=-1&endrow=500' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table)
        self.assertEqual(response.content, test_data_json)

        # index not a number -> bad request
        response = self.client.get('/api/wfmodules/%d/render?startrow=0&endrow=frog' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    # can we take one out?
    def test_wf_module_delete(self):
        # add a new one to delete; don't mess with other tests
        wfmodule4 = add_new_wf_module(self.workflow1, self.module2_version, 3)

        response = self.client.delete('/api/wfmodules/%d' % wfmodule4.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(WfModule.DoesNotExist):
            WfModule.objects.get(pk=wfmodule4.id, workflow=self.workflow1)  # must really be gone

    # /input is just a /render on the previous module
    def test_wf_module_input(self):
        # First module: no prior input, should be empty result
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(pd.DataFrame())
        self.assertEqual(response.content, test_data_json)

        # Second module: input should be test data produced by first module
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json = make_render_json(self.test_table)
        self.assertEqual(response.content, test_data_json)

        # Third module: should be same as second, as second module is NOP
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, test_data_json)

    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        text1 = 'just pretend this is json'
        text2 = 'and this is a later version'
        firstver = self.wfmodule1.store_data(text1)
        self.wfmodule1.set_stored_data_version(firstver)
        secondver = self.wfmodule1.store_data(text2)

        # retrieve version list through the API
        response = self.client.get('/api/wfmodules/%d/dataversion' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        versiondata = {
            "versions": [
                secondver.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                firstver.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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
        self.assertEqual(self.wfmodule1.get_stored_data_version(), secondver)


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
