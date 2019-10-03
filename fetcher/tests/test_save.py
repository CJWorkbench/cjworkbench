import math
from pathlib import Path
from unittest.mock import patch
from django.test import override_settings
from cjwkernel.types import FetchResult
from cjwkernel.tests.util import parquet_file
from cjwstate.models import StoredObject, WfModule, Workflow
from cjwstate.tests.utils import DbTestCase
from fetcher.save import save_result_if_changed


async def async_noop(*args, **kwargs):
    pass


@patch("server.websockets._workflow_group_send", async_noop)
@patch("server.websockets.queue_render_if_listening", async_noop)
class SaveTests(DbTestCase):
    def test_store_if_changed(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save_result_if_changed(
                    workflow.id, wf_module, FetchResult(parquet_path)
                )
            )
        self.assertEqual(StoredObject.objects.count(), 1)

        # store same data again (different file); should not create a new one
        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save_result_if_changed(
                    workflow.id, wf_module, FetchResult(parquet_path)
                )
            )
        self.assertEqual(StoredObject.objects.count(), 1)

        # changed table should create new
        with parquet_file({"B": ["x"], "A": [1]}) as parquet_path:
            self.run_with_async_db(
                save_result_if_changed(
                    workflow.id, wf_module, FetchResult(parquet_path)
                )
            )
        self.assertEqual(StoredObject.objects.count(), 2)

    def test_storage_limits(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        stored_objects = wf_module.stored_objects  # not queried yet

        # Store 1 version, to measure its size
        with parquet_file({"A": ["abc0"]}) as parquet_path:
            self.run_with_async_db(
                save_result_if_changed(
                    workflow.id, wf_module, FetchResult(parquet_path)
                )
            )
            one_size = parquet_path.stat().st_size

        # Store 3 more versions, given enough room for 4 tables
        with override_settings(MAX_STORAGE_PER_MODULE=math.ceil(one_size * 4.2)):
            for i in range(1, 4):
                with parquet_file({"A": ["abc" + str(i)]}) as parquet_path:
                    self.run_with_async_db(
                        save_result_if_changed(
                            workflow.id, wf_module, FetchResult(parquet_path)
                        )
                    )
        self.assertEqual(stored_objects.count(), 4)  # all four were saved

        # Store 1 more version, given enough room for 2 tables
        with override_settings(MAX_STORAGE_PER_MODULE=math.ceil(one_size * 2.2)):
            with parquet_file({"A": ["abc4"]}) as parquet_path:
                self.run_with_async_db(
                    save_result_if_changed(
                        workflow.id, wf_module, FetchResult(parquet_path)
                    )
                )
        self.assertEqual(stored_objects.count(), 2)  # some were deleted

        # Store 1 more version, given enough room for _not even one_ table
        with override_settings(MAX_STORAGE_PER_MODULE=math.ceil(one_size * 0.3)):
            with parquet_file({"A": ["abc5"]}) as parquet_path:
                self.run_with_async_db(
                    save_result_if_changed(
                        workflow.id, wf_module, FetchResult(parquet_path)
                    )
                )
        self.assertEqual(stored_objects.count(), 1)

    def test_race_deleted_workflow(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        workflow_id = workflow.id

        workflow.delete()

        # Don't crash
        self.run_with_async_db(
            save_result_if_changed(
                workflow_id, wf_module, FetchResult(Path("/not-checked"))
            )
        )

    def test_race_soft_deleted_wf_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", is_deleted=True
        )

        # Don't crash
        self.run_with_async_db(
            save_result_if_changed(
                workflow.id, wf_module, FetchResult(Path("/not-used"))
            )
        )
        self.assertEqual(wf_module.stored_objects.count(), 0)

    def test_race_hard_deleted_wf_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        WfModule.objects.filter(id=wf_module.id).delete()

        # Don't crash
        self.run_with_async_db(
            save_result_if_changed(
                workflow.id, wf_module, FetchResult(Path("/not-used"))
            )
        )
