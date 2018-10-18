from collections import namedtuple
import json
from unittest.mock import patch
from django.contrib.auth.models import User
import numpy as np
import pandas as pd
from rest_framework.test import APIRequestFactory
from rest_framework import status
from rest_framework.test import force_authenticate
from server.models import Module, Workflow
from server.modules.types import ProcessResult
from server.views.WfModule import wfmodule_detail, wfmodule_dataversion
from server.tests.utils import LoggedInTestCase, mock_csv_table, \
        mock_csv_table2


FakeSession = namedtuple('FakeSession', ['session_key'])


FakeCachedRenderResult = namedtuple('FakeCachedRenderResult', ['result'])


async def async_noop(*args, **kwargs):
    pass


test_data = pd.DataFrame({
    'Class': ['math', 'english', 'history', 'economics'],
    'M': [10, np.nan, 11, 20],
    'F': [12, 7, 13, 20],
})


test_data_json = {
    'start_row': 0,
    'end_row': 4,
    'rows': [
        {'Class': 'math', 'F': 12, 'M': 10.0},
        {'Class': 'english', 'F': 7, 'M': None},
        {'Class': 'history', 'F': 13, 'M': 11.0},
        {'Class': 'economics', 'F': 20, 'M': 20.0}
    ],
}

empty_data_json = {
    'start_row': 0,
    'end_row': 0,
    'rows': [],
}


@patch('server.models.Delta.schedule_execute', async_noop)
@patch('server.models.Delta.ws_notify', async_noop)
class WfModuleTests(LoggedInTestCase):
    # Test workflow with modules that implement a simple pipeline on test data
    def setUp(self):
        super().setUp()  # log in

        self.workflow = Workflow.objects.create(name='test', owner=self.user)
        self.wf_module1 = self.workflow.wf_modules.create(
            order=0,
            last_relevant_delta_id=1
        )
        self.wf_module2 = self.workflow.wf_modules.create(
            order=1,
            last_relevant_delta_id=2
        )

        self.log_patcher = patch('server.utils.log_user_event')
        self.log_patch = self.log_patcher.start()
        self.factory = APIRequestFactory()

    def tearDown(self):
        self.log_patcher.stop()
        super().tearDown()

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
        module = Module.objects.create(name='Hi', id_name='hi', dispatch='hi')
        module_version = module.module_versions.create(
            source_version_hash='1.0'
        )
        wf_module = self.workflow.wf_modules.create(
            order=2,
            last_relevant_delta_id=3,
            module_version_id=module_version.id
        )
        wf_module.create_parametervals({})
        wf_module.store_fetched_table(pd.DataFrame({'A': [1]}))
        wf_module.store_fetched_table(pd.DataFrame({'A': [2]}))

        response = self.client.get('/api/wfmodules/%d/' % wf_module.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], wf_module.id)
        self.assertEqual(response.data['workflow'], self.workflow.id)
        self.assertEqual(response.data['notes'], wf_module.notes)
        self.assertEqual(response.data['module_version']['module'], module.id)
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
        self.assertEqual(len(response.data['versions']['versions']), 2)
        self.assertEqual(response.data['html_output'],
                         wf_module.module_version.html_output)

        response = self.client.get('/api/wfmodules/10000/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_wf_module_params_patch(self):
        module = Module.objects.create(name='Hi', id_name='hi', dispatch='hi')
        module_version = module.module_versions.create(
            source_version_hash='1.0'
        )
        module_version.parameter_specs.create(id_name='arg', order=0,
                                              type='string', def_value='')
        wf_module = self.workflow.wf_modules.create(
            order=2,
            module_version=module_version
        )
        wf_module.create_parametervals({})

        response = self.client.patch(
            f'/api/wfmodules/{wf_module.id}/params',
            json.dumps({ 'values': { 'arg': 'newval' }}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(wf_module.get_params().get_param_string('arg'),
                         'newval')

    def test_wf_module_params_patch_missing_values(self):
        response = self.client.patch(
            f'/api/wfmodules/{self.wf_module1.id}/params',
            json.dumps({ 'value': { 'arg': 'newval' }}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        parsed = json.loads(response.content)
        self.assertEqual(parsed, {'error': 'Request missing "values" Object'})

    def test_wf_module_params_patch_invalid_values(self):
        response = self.client.patch(
            f'/api/wfmodules/{self.wf_module1.id}/params',
            json.dumps({ 'values': ['arg', 'newval']}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        parsed = json.loads(response.content)
        self.assertEqual(parsed,
                         {'error': 'Request "values" must be an Object'})

    def test_missing_module(self):
        # If the WfModule references a Module that does not exist, we should
        # get a placeholder
        wf_module = self.workflow.wf_modules.create(
            order=2,
            last_relevant_delta_id=3
        )
        wf_module.cache_render_result(3,
                                      ProcessResult(pd.DataFrame({'A': [1]})))
        wf_module.save()

        response = self.client.get('/api/wfmodules/%d/' % wf_module.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)

        parsed = json.loads(response.content)
        self.assertEqual(parsed['module_version']['module'], None)

        response = self.client.get('/api/wfmodules/%d/render' % wf_module.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['rows'], [{'A': 1}])

    # Test some json conversion gotchas we encountered during development
    def test_pandas_13258(self):
        # simple test case where Pandas produces int64 column type, and json
        # conversion throws ValueError
        # https://github.com/pandas-dev/pandas/issues/13258#issuecomment-326671257
        self.wf_module2.cache_render_result(2, ProcessResult(
            pd.DataFrame({'A': [1, 2]}, dtype='int64')
        ))
        self.wf_module2.save()

        response = self.client.get('/api/wfmodules/%d/render' %
                                   self.wf_module2.id)
        self.assertEqual(response.status_code, 200)

    def test_max_columns_returned(self):
        # Only at most 101 columns should be returned to the client
        # since we do not display more than 100. (This is a funky hack that
        # assumes the client will behave differently when it has >100 columns.)
        data = {}
        for i in range(0, 102):
            data[str(i)] = [1]
        self.wf_module2.cache_render_result(2,
                                            ProcessResult(pd.DataFrame(data)))
        self.wf_module2.save()

        response = self.client.get('/api/wfmodules/%d/render' %
                                   self.wf_module2.id)
        self.assertEqual(response.status_code, 200)
        # Max 101 columns of data
        self.assertEqual(len(json.loads(response.content)['rows'][0]), 101)

    def test_wf_module_render(self):
        self.wf_module2.cache_render_result(2, ProcessResult(test_data))
        self.wf_module2.save()

        response = self.client.get('/api/wfmodules/%d/render'
                                   % self.wf_module2.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

    def test_wf_module_render_only_rows(self):
        self.wf_module2.cache_render_result(2, ProcessResult(test_data))
        self.wf_module2.save()

        response = self.client.get(
            '/api/wfmodules/%d/render?startrow=1&endrow=3'
            % self.wf_module2.id
        )
        self.assertIs(response.status_code, status.HTTP_200_OK)
        body = json.loads(response.content)
        self.assertEqual(body['rows'], test_data_json['rows'][1:3])
        self.assertEqual(body['start_row'], 1)
        self.assertEqual(body['end_row'], 3)

    def test_wf_module_render_clip_out_of_bounds(self):
        self.wf_module2.cache_render_result(2, ProcessResult(test_data))
        self.wf_module2.save()

        # index out of bounds should clip
        response = self.client.get(
            '/api/wfmodules/%d/render?startrow=-1&endrow=500'
            % self.wf_module2.id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), test_data_json)

    def test_wf_module_render_invalid_endrow(self):
        # index not a number -> bad request
        response = self.client.get(
            '/api/wfmodules/%d/render?startrow=0&endrow=frog'
            % self.wf_module2.id
        )
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wf_module_delete(self):
        response = self.client.delete('/api/wfmodules/%d' % self.wf_module2.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        wf_modules = list(self.workflow.wf_modules.all())
        self.assertEqual(len(wf_modules), 1)
        self.assertEqual(wf_modules[0].pk, self.wf_module1.id)

    # test stored versions of data: create, retrieve, set, list, and views
    def test_wf_module_data_versions(self):
        firstver = self.wf_module1.store_fetched_table(mock_csv_table)
        self.wf_module1.set_fetched_data_version(firstver)
        secondver = self.wf_module1.store_fetched_table(mock_csv_table2)

        # retrieve version list through the API
        response = self.client.get('/api/wfmodules/%d/dataversion' %
                                   self.wf_module1.id)
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
        request = self._build_patch('/api/wfmodules/%d/dataversion' %
                                    self.wf_module1.id,
                                    {'selected': secondver.strftime("%Y-%m-%dT%H:%M:%S.%fZ")},
                                    user=self.user)
        response = wfmodule_dataversion(request, pk=self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)
        self.wf_module1.refresh_from_db()
        self.assertEqual(self.wf_module1.get_fetched_data_version(), secondver)


    # test Wf Module Notes change API
    def test_wf_module_notes_post(self):
        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    {'notes': 'wow such doge'},
                                    user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new value back
        response = self.client.get('/api/wfmodules/%d/' % self.wf_module1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'wow such doge')

        # Test for error on missing notes field (and no other patachable fields)
        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    {'notnotes': 'forthcoming error'},
                                    user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test set/get update interval
    def test_wf_module_update_settings(self):
        settings = {'auto_update_data': True,
                    'update_interval': 5,
                    'update_units': 'weeks'}

        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # see that we get the new values back
        response = self.client.get('/api/wfmodules/%d/' % self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['auto_update_data'], True)
        self.assertEqual(response.data['update_interval'], 5)
        self.assertEqual(response.data['update_units'], 'weeks')

        # Check we logged the event
        # #160041803
        self.log_patch.assert_called_once()
        self.assertEqual(self.log_patch.call_args[0][1], 'Enabled auto-update')

    # Test set/get update interval
    def test_wf_module_update_settings_missing_units(self):
        settings = {'auto_update_data': True,
                    'update_interval': 5,
                    }

        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wf_module_update_settings_missing_interval(self):
        settings = {'auto_update_data': True, 'update_units': 'days'}
        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wf_module_update_settings_bad_units(self):
        settings = {'auto_update_data': True, 'update_interval': 66, 'update_units': 'pajama'}
        request = self._build_patch('/api/wfmodules/%d' % self.wf_module1.id,
                                    settings, user=self.user)
        response = wfmodule_detail(request, pk=self.wf_module1.id)
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_value_counts_str(self):
        self.wf_module2.cache_render_result(2, ProcessResult(
            pd.DataFrame({
                'A': ['a', 'b', 'b', 'a', 'c', np.nan],
                'B': ['x', 'x', 'x', 'x', 'x', 'x'],
            })
        ))
        self.wf_module2.save()

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/value-counts?column=A'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {'values': {'a': 2, 'b': 2, 'c': 1}}
        )

    def test_value_counts_cast_to_str(self):
        self.wf_module2.cache_render_result(2, ProcessResult(
            pd.DataFrame({'A': [1, 2, 3, 2, 1]})
        ))
        self.wf_module2.save()

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/value-counts?column=A'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(response.content),
            {'values': {'1': 2, '2': 2, '3': 1}}
        )

    def test_value_counts_param_invalid(self):
        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/value-counts'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json.loads(response.content), {
            'error': 'Missing a "column" parameter',
        })

    def test_value_counts_missing_column(self):
        self.wf_module2.cache_render_result(2, ProcessResult(
            pd.DataFrame({
                'A': ['a', 'b', 'b', 'a', 'c', np.nan],
                'B': ['x', 'x', 'x', 'x', 'x', 'x'],
            })
        ))
        self.wf_module2.save()

        response = self.client.get(
            f'/api/wfmodules/{self.wf_module2.id}/value-counts?column=C'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(json.loads(response.content), {
            'error': 'column "C" not found'
        })
