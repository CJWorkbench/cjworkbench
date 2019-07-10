from unittest.mock import patch
from django.conf import settings
from django.test import override_settings
import pandas as pd
from cjworkbench.types import ProcessResult
from server.models import StoredObject, Workflow
from server.tests.utils import DbTestCase, mock_csv_table
from fetcher.save import save_result_if_changed


async def async_noop(*args, **kwargs):
    pass


@patch("server.websockets._workflow_group_send", async_noop)
@patch("server.websockets.queue_render_if_listening", async_noop)
class SaveTests(DbTestCase):
    def test_store_if_changed(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        table = mock_csv_table.copy()
        self.run_with_async_db(
            save_result_if_changed(workflow.id, wf_module, ProcessResult(table))
        )
        self.assertEqual(StoredObject.objects.count(), 1)

        # store same table again, should not create a new one
        self.run_with_async_db(
            save_result_if_changed(workflow.id, wf_module, ProcessResult(table))
        )
        self.assertEqual(StoredObject.objects.count(), 1)

        # changed table should create new
        table = table.append(table, ignore_index=True)
        self.run_with_async_db(
            save_result_if_changed(workflow.id, wf_module, ProcessResult(table))
        )
        self.assertEqual(StoredObject.objects.count(), 2)

    @override_settings(MAX_STORAGE_PER_MODULE=1000)
    def test_storage_limits(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        table = mock_csv_table
        stored_objects = wf_module.stored_objects  # not queried yet

        for i in range(0, 4):
            # double table size, mimicking real-world growth of a table (but
            # faster)
            table = table.append(table, ignore_index=True)
            self.run_with_async_db(
                save_result_if_changed(workflow.id, wf_module, ProcessResult(table))
            )

            total_size = sum(stored_objects.values_list("size", flat=True))
            self.assertLessEqual(total_size, settings.MAX_STORAGE_PER_MODULE)

        n_objects = stored_objects.count()
        # test should have made the able big enoug to force there to be only
        # one version, eventually.
        # if not, increase table size/loop iterations, or decrease limit
        self.assertEqual(n_objects, 1)

    def test_race_deleted_workflow(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}))

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        workflow.delete()

        # Don't crash
        self.run_with_async_db(save_result_if_changed(workflow.id, wf_module, result))
        assert True

    def test_race_soft_deleted_wf_module(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}))

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, is_deleted=True)

        # Don't crash
        self.run_with_async_db(save_result_if_changed(workflow.id, wf_module, result))
        assert True

    def test_race_hard_deleted_wf_module(self):
        result = ProcessResult(pd.DataFrame({"A": [1]}))

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0)

        wf_module.delete()

        # Don't crash
        self.run_with_async_db(save_result_if_changed(workflow.id, wf_module, result))
        assert True
