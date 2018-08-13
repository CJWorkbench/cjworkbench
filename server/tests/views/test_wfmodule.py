from collections import namedtuple
import json
from unittest.mock import patch
from django.contrib.auth.models import User
import numpy as np
import pandas as pd
from rest_framework.test import APIRequestFactory
from rest_framework import status
from rest_framework.test import force_authenticate
from server.models import Module, WfModule, Workflow
from server.modules.types import ProcessResult
from server.views.WfModule import wfmodule_detail, wfmodule_dataversion
from server.tests.test_wfmodule import WfModuleTestsBase
from server.tests.utils import LoggedInTestCase, mock_csv_table, \
        mock_csv_table2, add_new_workflow, add_new_wf_module, \
        create_testdata_workflow


FakeSession = namedtuple('FakeSession', ['session_key'])

test_data_json = {
    'total_rows': 4,
    'start_row': 0,
    'end_row': 4,  # XXX should be 3? Will that break anything?
    'columns': ['Class', 'M', 'F'],
    'rows': [
        {'Class': 'math', 'F': 12, 'M': 10.0},
        {'Class': 'english', 'F': 7, 'M': None},
        {'Class': 'history', 'F': 13, 'M': 11.0},
        {'Class': 'economics', 'F': 20, 'M': 20.0}
    ],
    'column_types': [
        'text',
        'number',
        'number'
    ]
}

empty_data_json = {
    'total_rows': 0,
    'start_row': 0,
    'end_row': 0,
    'columns': [],
    'rows': [],
    'column_types': [],
}


class WfModuleTests(LoggedInTestCase, WfModuleTestsBase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super(WfModuleTests, self).setUp()  # log in
        self.createTestWorkflow()
        self.factory = APIRequestFactory()

    def _augment_request(self, request, user: User,
                         session_key: str) -> None:
        if user:
            force_authenticate(request, user=user)
        request.session = FakeSession(session_key)

    def _build_patch(self, *args, user: User=None, session_key: str='a-key',
                     **kwargs):
        request = self.factory.patch(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    def _build_put(self, *args, user: User=None, session_key: str='a-key',
                   **kwargs):
        request = self.factory.put(*args, **kwargs)
        self._augment_request(request, user, session_key)
        return request

    # TODO test parameter values returned from this call
    def test_wf_module_detail_get(self):
        # Also tests [Workflow, Module, WfModule].get
        workflow = Workflow.objects.get(name='Workflow 1')
        module_id = Module.objects.get(name='Module 1').id
        wf_module = WfModule.objects.get(
            workflow_id=workflow.id,
            module_version__module__name='Module 1'
        )
        wf_module_versions = {
            'versions': wf_module.list_fetched_data_versions(),
            'selected': wf_module.get_fetched_data_version()
        }

        response = self.client.get('/api/wfmodules/%d/' % wf_module.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], wf_module.id)
        self.assertEqual(response.data['workflow'], workflow.id)
        self.assertEqual(response.data['notes'], wf_module.notes)
        self.assertEqual(response.data['module_version']['module'], module_id)
        self.assertEqual(response.data['status'], wf_module.status)
        self.assertEqual(response.data['error_msg'], wf_module.error_msg)
        self.assertEqual(response.data['is_collapsed'], wf_module.is_collapsed)
        self.assertEqual(response.data['auto_update_data'],
                         wf_module.auto_update_data)
        self.assertEqual(response.data['last_update_check'],
                         wf_module.last_update_check)
        # defaults here to avoid time unit conversion
        self.assertEqual(response.data['update_interval'], 1)
        self.assertEqual(response.data['update_units'], 'days')
        self.assertEqual(response.data['notifications'],
                         wf_module.notifications)
        self.assertEqual(response.data['has_unseen_notification'], False)
        self.assertEqual(response.data['versions'], wf_module_versions)
        self.assertEqual(response.data['html_output'],
                         wf_module.module_version.html_output)

        response = self.client.get('/api/wfmodules/10000/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_module(self):
        # If the WfModule references a Module that does not exist, we should
        # get a placeholder
        workflow = add_new_workflow('Missing module')
        wfm = add_new_wf_module(workflow, None, 0)
        response = self.client.get('/api/wfmodules/%d/' % wfm.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        parsed = json.loads(response.content)
        self.assertEqual(parsed['module_version']['module'], None)

        response = self.client.get('/api/wfmodules/%d/render' % wfm.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), empty_data_json)

    # Test some json conversion gotchas we encountered during development
    def test_pandas_13258(self):
        # simple test case where Pandas produces int64 column type, and json
        # conversion throws ValueError
        # https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257
        workflow = create_testdata_workflow(csv_text='A,B,C,D\n1,2,3,4')
        response = self.client.get('/api/wfmodules/%d/render' %
                                   workflow.wf_modules.first().id)
        self.assertIs(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['column_types'],
                         ['number', 'number', 'number', 'number'])

    def test_pandas_no_header(self):
        # When no header row, Pandas uses int64s as column names, and
        # json.dumps(list(table)) throws ValueError
        workflow = create_testdata_workflow(csv_text='1,2,3,4\n1,2,3,4')
        response = self.client.get('/api/wfmodules/%d/render' %
                                   workflow.wf_modules.first().id)
        self.assertIs(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['columns'],
                         ['1', '2', '3', '4'])
        self.assertEqual(json.loads(response.content)['column_types'],
                         ['number', 'number', 'number', 'number'])

    def test_wf_module_render_get(self):
        # First module: creates test data
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

        # second module: NOP
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

        # Third module: doubles M column
        response = self.client.get('/api/wfmodules/%d/render' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json1 = json.loads(json.dumps(test_data_json))
        for row in test_data_json1['rows']:
            if row['M'] is not None:
                row['M'] *= 2
        self.assertEqual(json.loads(response.content), test_data_json1)

        # Now test retrieving specified rows only
        response = self.client.get('/api/wfmodules/%d/render?startrow=1' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json2 = json.loads(json.dumps(test_data_json))
        test_data_json2['start_row'] = 1
        test_data_json2['rows'] = test_data_json2['rows'][1:]
        self.assertEqual(json.loads(response.content), test_data_json2)

        response = self.client.get('/api/wfmodules/%d/render?startrow=1&endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json3 = json.loads(json.dumps(test_data_json))
        test_data_json3['start_row'] = 1
        test_data_json3['end_row'] = 3
        test_data_json3['rows'] = test_data_json3['rows'][1:3]
        self.assertEqual(json.loads(response.content), test_data_json3)

        response = self.client.get('/api/wfmodules/%d/render?endrow=3' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        test_data_json4 = json.loads(json.dumps(test_data_json))
        test_data_json4['end_row'] = 3
        test_data_json4['rows'] = test_data_json4['rows'][0:3]
        self.assertEqual(json.loads(response.content), test_data_json4)

        # index out of bounds should clip
        response = self.client.get('/api/wfmodules/%d/render?startrow=-1&endrow=500' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

        # index not a number -> bad request
        response = self.client.get('/api/wfmodules/%d/render?startrow=0&endrow=frog' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


    # can we take one out?
    def test_wf_module_delete(self):
        # add a new one to delete; don't mess with other tests
        wfmodule4 = add_new_wf_module(self.workflow1, self.module2_version, 3)
        self.workflow1.selected_wf_module = 3
        self.workflow1.save()

        response = self.client.delete('/api/wfmodules/%d' % wfmodule4.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WfModule.objects.filter(workflow=self.workflow1, pk=wfmodule4.id).exists())  # must really be gone

        # also check that deleting the selected module nullifies workflow.selected_wf_module
        self.workflow1.refresh_from_db()
        self.assertEqual(self.workflow1.selected_wf_module, 2)


    # /input is just a /render on the previous module
    def test_wf_module_input(self):
        # First module: no prior input, should be empty result
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), empty_data_json)

        # Second module: input should be test data produced by first module
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule2.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

        # Third module: should be same as second, as second module is NOP
        response = self.client.get('/api/wfmodules/%d/input' % self.wfmodule3.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

    # tests for the /columns API
    def test_wf_module_columns(self):
        # We only need to check for one module since the output is pretty much the same
        # Dates are not tested here because the test WF cannot be fed date data
        response = self.client.get('/api/wfmodules/%d/columns' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), [
            {"name": "Class", "type": "text"},
            {"name": "M", "type": "number"},
            {"name": "F", "type": "number"}
        ])

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
        request = self._build_patch('/api/wfmodules/%d/dataversion' % self.wfmodule1.id,
                                    {'selected': secondver.strftime("%Y-%m-%dT%H:%M:%S.%fZ")},
                                    user=self.user)
        response = wfmodule_dataversion(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.wfmodule1.refresh_from_db()
        self.assertEqual(self.wfmodule1.get_fetched_data_version(), secondver)


    # test Wf Module Notes change API
    def test_wf_module_notes_post(self):
        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    {'notes': 'wow such doge'},
                                    user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'wow such doge')

        # Test for error on missing notes field (and no other patachable fields)
        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    {'notnotes': 'forthcoming error'},
                                    user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test set/get update interval
    def test_wf_module_update_settings(self):
        settings = {'auto_update_data': True,
                    'update_interval': 5,
                    'update_units': 'weeks'}

        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new values back
        response = self.client.get('/api/wfmodules/%d/' % self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['auto_update_data'], True)
        self.assertEqual(response.data['update_interval'], 5)
        self.assertEqual(response.data['update_units'], 'weeks')

    # Test set/get update interval
    def test_wf_module_update_settings_missing_units(self):
        settings = {'auto_update_data': True,
                    'update_interval': 5,
                    }

        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wf_module_update_settings_missing_interval(self):
        settings = {'auto_update_data': True, 'update_units': 'days'}
        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wf_module_update_settings_bad_units(self):
        settings = {'auto_update_data': True, 'update_interval': 66, 'update_units': 'pajama'}
        request = self._build_patch('/api/wfmodules/%d' % self.wfmodule1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wfmodule1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


class WfModuleInputValueCountsTest(LoggedInTestCase):
    def setUp(self):
        super().setUp()

        self.workflow = Workflow.objects.create(owner=self.user)
        self.wf_module1 = self.workflow.wf_modules.create(order=0)
        self.wf_module2 = self.workflow.wf_modules.create(order=1)

    def test_value_counts_missing_input_module(self):
        self.wf_module1.delete()

        # First module: no prior input, should be 404
        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(json.loads(response.content), {
            'error': 'Module has no input'
        })

    @patch('server.execute.execute_wfmodule')
    @patch('server.models.WfModule.get_param_column')
    def test_value_counts_str(self, get_param, execute):
        get_param.return_value = 'A'
        execute.return_value = ProcessResult(pd.DataFrame({
            'A': ['a', 'b', 'b', 'a', 'c', np.nan],
            'B': ['x', 'x', 'x', 'x', 'x', 'x'],
        }))

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {'values': {'a': 2, 'b': 2, 'c': 1}}
        )

    @patch('server.execute.execute_wfmodule')
    @patch('server.models.WfModule.get_param_column')
    def test_value_counts_cast_to_str(self, get_param, execute):
        get_param.return_value = 'A'
        execute.return_value = ProcessResult(pd.DataFrame({
            'A': [1, 2, 3, 2, 1],
        }))

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {'values': {'1': 2, '2': 2, '3': 1}}
        )

    @patch('server.execute.execute_wfmodule')
    @patch('server.models.WfModule.get_param_column')
    def test_value_counts_no_column(self, get_param, execute):
        get_param.return_value = ''
        execute.return_value = ProcessResult(pd.DataFrame({
            'A': ['a', 'b', 'b', 'a', 'c', np.nan],
            'B': ['x', 'x', 'x', 'x', 'x', 'x'],
        }))

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), {'values': {}})

    @patch('server.models.WfModule.get_param_column')
    def test_value_counts_param_invalid(self, get_param):
        get_param.side_effect = ValueError('(WfModule API should probably be KeyError)')

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(json.loads(response.content), {
            'error': 'Module is missing a "column" parameter',
        })

    @patch('server.execute.execute_wfmodule')
    @patch('server.models.WfModule.get_param_column')
    def test_value_counts_missing_column(self, get_param, execute):
        get_param.return_value = 'C'
        execute.return_value = ProcessResult(pd.DataFrame({
            'A': ['a', 'b', 'b', 'a', 'c', np.nan],
            'B': ['x', 'x', 'x', 'x', 'x', 'x'],
        }))

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/input-value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(json.loads(response.content), {
            'error': 'column "C" not found'
        })
