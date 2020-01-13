from unittest.mock import patch
from django.utils import timezone
from cjwkernel.types import FetchResult
from cjwkernel.tests.util import parquet_file
from cjwstate import clientside, rabbitmq, storedobjects
from cjwstate.models import WfModule, Workflow
from cjwstate.models.commands import ChangeDataVersionCommand
from cjwstate.tests.utils import DbTestCase
from fetcher import save


async def async_noop(*args, **kwargs):
    pass


@patch.object(rabbitmq, "queue_render_if_consumers_are_listening", async_noop)
class SaveTests(DbTestCase):
    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_create_result(self, send_update):
        send_update.side_effect = async_noop

        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", is_busy=True, fetch_error="previous error"
        )
        now = timezone.datetime(2019, 10, 22, 12, 22, tzinfo=timezone.utc)

        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save.create_result(
                    workflow.id, wf_module, FetchResult(parquet_path), now
                )
            )
        self.assertEqual(wf_module.stored_objects.count(), 1)

        self.assertEqual(wf_module.fetch_error, "")
        self.assertEqual(wf_module.is_busy, False)
        self.assertEqual(wf_module.last_update_check, now)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.fetch_error, "")
        self.assertEqual(wf_module.is_busy, False)
        self.assertEqual(wf_module.last_update_check, now)

        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                steps={
                    wf_module.id: clientside.StepUpdate(
                        is_busy=False, last_fetched_at=now
                    )
                }
            ),
        )

        workflow.refresh_from_db()
        self.assertIsInstance(workflow.last_delta, ChangeDataVersionCommand)

    @patch.object(rabbitmq, "send_update_to_workflow_clients")
    def test_mark_result_unchanged(self, send_update):
        send_update.side_effect = async_noop
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", is_busy=True, fetch_error="previous error"
        )
        now = timezone.datetime(2019, 10, 22, 12, 22, tzinfo=timezone.utc)

        self.run_with_async_db(save.mark_result_unchanged(workflow.id, wf_module, now))
        self.assertEqual(wf_module.stored_objects.count(), 0)

        self.assertEqual(wf_module.fetch_error, "previous error")
        self.assertEqual(wf_module.is_busy, False)
        self.assertEqual(wf_module.last_update_check, now)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.fetch_error, "previous error")
        self.assertEqual(wf_module.is_busy, False)
        self.assertEqual(wf_module.last_update_check, now)

        send_update.assert_called_with(
            workflow.id,
            clientside.Update(
                steps={
                    wf_module.id: clientside.StepUpdate(
                        is_busy=False, last_fetched_at=now
                    )
                }
            ),
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", async_noop)
    @patch.object(storedobjects, "enforce_storage_limits")
    def test_storage_limits(self, limit):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")

        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save.create_result(
                    workflow.id, wf_module, FetchResult(parquet_path), timezone.now()
                )
            )
        limit.assert_called_with(wf_module)

    def test_race_deleted_workflow(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        workflow_id = workflow.id
        workflow.delete()

        # Don't crash
        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save.create_result(
                    workflow_id, wf_module, FetchResult(parquet_path), timezone.now()
                )
            )

    def test_race_soft_deleted_wf_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", is_deleted=True
        )
        workflow_id = workflow.id
        workflow.delete()

        # Don't crash
        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save.create_result(
                    workflow_id, wf_module, FetchResult(parquet_path), timezone.now()
                )
            )
        self.assertEqual(wf_module.stored_objects.count(), 0)

    def test_race_hard_deleted_wf_module(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=0, slug="step-1")
        WfModule.objects.filter(id=wf_module.id).delete()

        # Don't crash
        with parquet_file({"A": [1], "B": ["x"]}) as parquet_path:
            self.run_with_async_db(
                save.create_result(
                    workflow.id, wf_module, FetchResult(parquet_path), timezone.now()
                )
            )
