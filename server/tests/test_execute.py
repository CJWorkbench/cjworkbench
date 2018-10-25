import asyncio
from unittest.mock import patch
from asgiref.sync import async_to_sync
import pandas as pd
from server.tests.utils import DbTestCase, create_testdata_workflow, \
        load_and_add_module, get_param_by_id_name
from server.execute import execute_workflow
from server.modules.types import ProcessResult


table_csv = 'A,B\n1,2\n3,4'
table_dataframe = pd.DataFrame({'A': [1, 3], 'B': [2, 4]})


fake_future = asyncio.Future()
fake_future.set_result(None)


async def fake_send(*args, **kwargs):
    pass


def cached_render_result_revision_list(workflow):
    return list(workflow.wf_modules.values_list(
        'cached_render_result_delta_id',
        flat=True
    ))


class ExecuteTests(DbTestCase):
    def test_execute_revision_0(self):
        # Don't crash on a new workflow (rev=0, no caches)
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)
        async_to_sync(execute_workflow)(workflow)
        wf_module2.refresh_from_db()
        result = wf_module2.get_cached_render_result().result

        self.assertEqual(result, ProcessResult(table_dataframe))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 0])

    @patch('server.websockets.ws_client_send_delta_async', fake_send)
    def test_execute_new_revision(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        async_to_sync(execute_workflow)(workflow)

        pval = get_param_by_id_name('colnames', wf_module=wf_module2)
        pval.set_value('A')

        wf_module2.last_relevant_delta_id = 2
        wf_module2.save(update_fields=['last_relevant_delta_id'])

        async_to_sync(execute_workflow)(workflow)

        wf_module2.refresh_from_db()
        result = wf_module2.get_cached_render_result().result

        self.assertEqual(result, ProcessResult(table_dataframe[['A']]))
        self.assertEqual(cached_render_result_revision_list(workflow), [0, 2])

    @patch('server.websockets.ws_client_send_delta_async')
    def test_execute_mark_unreachable(self, send_delta_async):
        send_delta_async.return_value = fake_future

        workflow = create_testdata_workflow(table_csv)
        # Default pythoncode value is passthru
        wf_module2 = load_and_add_module('pythoncode', workflow=workflow)
        wf_module3 = load_and_add_module('selectcolumns', workflow=workflow,
                                         param_values={'drop_or_keep': 1,
                                                       'colnames': 'A,B'})

        async_to_sync(execute_workflow)(workflow)

        # Should set status of all modules to 'ok'
        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.status, 'ok')

        # Update parameter. Now module 2 will return an error.
        wf_module2.parameter_vals.get(parameter_spec__id_name='code') \
            .set_value('=ERROR')
        wf_module2.last_relevant_delta_id = 2
        wf_module3.last_relevant_delta_id = 2
        wf_module2.save(update_fields=['last_relevant_delta_id'])
        wf_module3.save(update_fields=['last_relevant_delta_id'])

        # (more integration-test-y) now their statuses are 'busy' because they
        # await render (and not because they're fetching)
        wf_module2.refresh_from_db()
        self.assertEqual(wf_module2.status, 'busy')
        self.assertEqual(wf_module2.is_busy, False)  # is_busy is for fetch
        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.status, 'busy')
        self.assertEqual(wf_module2.is_busy, False)  # is_busy is for fetch

        async_to_sync(execute_workflow)(workflow)

        # Now we expect module 2 to have 'error', 3 to have 'unreachable'
        wf_module2.refresh_from_db()
        self.assertEqual(wf_module2.status, 'error')
        wf_module3.refresh_from_db()
        self.assertEqual(wf_module3.status, 'unreachable')

        # send_delta_async.assert_called_with(workflow.id, {
        #     'updateWfModules': {
        #         str(wf_module2.id): {
        #             'error_msg': 'ERROR',
        #             'status': 'error',
        #             'quick_fixes': [],
        #             'output_columns': [],
        #             'last_relevant_delta_id':
        #                 wf_module2.last_relevant_delta_id
        #         }
        #     }
        # })

        send_delta_async.assert_called_with(workflow.id, {
            'updateWfModules': {
                str(wf_module3.id): {
                    'error_msg': '',
                    'status': 'unreachable',
                    'quick_fixes': [],
                    'output_columns': [],
                    'output_n_rows': 0,
                    'last_relevant_delta_id':
                    wf_module3.last_relevant_delta_id,
                    'cached_render_result_delta_id':
                    wf_module2.last_relevant_delta_id,
                }
            }
        })

    def test_execute_cache_hit(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow)

        async_to_sync(execute_workflow)(workflow)
        wf_module2.refresh_from_db()
        result1 = wf_module2.get_cached_render_result().result

        with patch('server.dispatch.module_dispatch_render') as mdr:
            async_to_sync(execute_workflow)(workflow)
            wf_module2.refresh_from_db()
            result2 = wf_module2.get_cached_render_result().result
            self.assertFalse(mdr.called)
            self.assertEqual(result2, result1)

    def test_resume_without_rerunning_unneeded_renders(self):
        workflow = create_testdata_workflow(table_csv)
        wf_module1 = workflow.wf_modules.first()
        wf_module2 = load_and_add_module('selectcolumns', workflow=workflow,
                                         last_relevant_delta_id=1)
        wf_module1.last_relevant_delta_id = 1
        wf_module1.save()

        async_to_sync(execute_workflow)(workflow)

        wf_module2.refresh_from_db()
        expected = wf_module2.get_cached_render_result().result
        wf_module2.last_relevant_delta_id = 2
        wf_module2.save()

        with patch('server.dispatch.module_dispatch_render') as mdr:
            mdr.return_value = expected
            async_to_sync(execute_workflow)(workflow)
            mdr.assert_called_once()
            wf_module2.refresh_from_db()
            result = wf_module2.get_cached_render_result().result
            self.assertEqual(result, expected)

    @patch('server.notifications.email_output_delta')
    def test_email_delta(self, email):
        workflow = create_testdata_workflow(table_csv)
        wf_module1 = workflow.wf_modules.first()
        wf_module1.notifications = True
        wf_module1.save()
        async_to_sync(execute_workflow)(workflow)

        email.assert_called()

        wf_module1.refresh_from_db()
        self.assertTrue(wf_module1.has_unseen_notification)

    @patch('server.notifications.email_output_delta')
    def test_email_no_delta_when_not_changed(self, email):
        workflow = create_testdata_workflow(table_csv)
        wf_module1 = workflow.wf_modules.first()
        wf_module1.notifications = True
        wf_module1.save()
        async_to_sync(execute_workflow)(workflow)  # sends one email
        async_to_sync(execute_workflow)(workflow)  # should not email

        email.assert_called_once()
