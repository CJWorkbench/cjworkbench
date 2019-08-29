import asyncio
from pathlib import Path
from typing import Callable
from unittest.mock import Mock, patch
import uuid
from dataclasses import dataclass
from dateutil import parser
from django.contrib.auth.models import User
from django.utils import timezone
import pandas as pd
from pandas.testing import assert_frame_equal
from cjworkbench.sync import database_sync_to_async
from cjwkernel.pandas.types import ProcessResult
from cjwstate import parquet
from cjwstate.rendercache import cache_render_result
from server import minio
from server.models import LoadedModule, ModuleVersion, StoredObject, WfModule, Workflow
from server.models.commands import InitWorkflowCommand
from server.models.param_dtype import ParamDType
from server.tests.utils import DbTestCase
from fetcher import fetch


future_none = asyncio.Future()
future_none.set_result(None)


async def async_noop(*args, **kwargs):
    pass


def DefaultMigrateParams(params):
    return params


class FetchTests(DbTestCase):
    def _store_fetched_table(
        self, wf_module: WfModule, table: pd.DataFrame
    ) -> StoredObject:
        key = f"{wf_module.workflow_id}/{wf_module.id}/{uuid.uuid1()}"
        size = parquet.write(minio.StoredObjectsBucket, key, table)
        return wf_module.stored_objects.create(
            bucket=minio.StoredObjectsBucket,
            key=key,
            size=size,
            hash="this test ignores hashes",
        )

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    @patch("fetcher.save.save_result_if_changed")
    def test_fetch_wf_module(self, save_result, load_module):
        result = ProcessResult(pd.DataFrame({"A": [1]}), error="hi")

        async def fake_fetch(*args, **kwargs):
            return result

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.param_schema = ParamDType.Dict({})
        fake_module.migrate_params.side_effect = lambda x: x
        fake_module.fetch.side_effect = fake_fetch

        save_result.side_effect = async_noop

        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=parser.parse("Aug 28 1999 2:24PM UTC"),
            update_interval=600,
        )
        wf_module._module_version = ModuleVersion(spec={"parameters": []})

        now = parser.parse("Aug 28 1999 2:24:02PM UTC")
        due_for_update = parser.parse("Aug 28 1999 2:34PM UTC")

        self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))

        save_result.assert_called_with(workflow.id, wf_module, result)

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.last_update_check, now)
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch("fetcher.save.save_result_if_changed")
    def test_fetch_deleted_wf_module(self, save_result):
        save_result.side_effect = async_noop

        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0, slug="step-1", module_id_name="deleted_module"
        )

        now = parser.parse("Aug 28 1999 2:24:02PM UTC")
        with self.assertLogs(fetch.__name__, level="INFO") as cm:
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))
            self.assertRegex(cm.output[0], r"fetch\(\) deleted module 'deleted_module'")

        save_result.assert_called_with(
            workflow.id,
            wf_module,
            ProcessResult(error="Cannot fetch: module was deleted"),
        )

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    def test_fetch_wf_module_skip_missed_update(self, load_module):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=parser.parse("Aug 28 1999 2:24PM UTC"),
            update_interval=600,
        )

        load_module.side_effect = Exception("caught")  # least-code test case

        now = parser.parse("Aug 28 1999 2:34:02PM UTC")
        due_for_update = parser.parse("Aug 28 1999 2:44PM UTC")

        with self.assertLogs(fetch.__name__):
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))

        wf_module.refresh_from_db()
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    @patch("fetcher.save.save_result_if_changed")
    def test_fetch_ignore_wf_module_deleted_when_updating(
        self, save_result, load_module
    ):
        """
        It's okay if wf_module is gone when updating wf_module.next_update.
        """
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=parser.parse("Aug 28 1999 2:24PM UTC"),
            update_interval=600,
        )

        async def fake_fetch(*args, **kwargs):
            return ProcessResult(pd.DataFrame({"A": [1]}))

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.migrate_params.side_effect = lambda x: x
        fake_module.fetch.side_effect = fake_fetch

        # We're testing what happens if wf_module disappears after save, before
        # update. To mock that, delete after fetch, when saving result.
        async def fake_save(workflow_id, wf_module, *args, **kwargs):
            @database_sync_to_async
            def do_delete():
                # We can't just call wf_module.delete(), because that will
                # change wf_module.id, which the code under test will notice.
                # We want to test what happens when wf_module.id is not None
                # and the value is not in the DB. Solution: look up a copy and
                # delete the copy.
                WfModule.objects.get(id=wf_module.id).delete()

            await do_delete()

        save_result.side_effect = fake_save

        now = parser.parse("Aug 28 1999 2:34:02PM UTC")

        # Assert fetch does not crash with
        # DatabaseError: Save with update_fields did not affect any rows
        with self.assertLogs(fetch.__name__, level="DEBUG"):
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    @patch("fetcher.save.save_result_if_changed")
    def test_fetch_poll_when_setting_next_update(self, save_result, load_module):
        """
        Handle `.auto_update_data` and `.update_interval` changing mid-fetch.
        """
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=parser.parse("Aug 28 1999 2:24PM UTC"),
            update_interval=600,
        )
        wf_module._module_version = ModuleVersion(spec={"parameters": []})

        async def fake_fetch(*args, **kwargs):
            return ProcessResult(pd.DataFrame({"A": [1]}))

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.param_schema = ParamDType.Dict({})
        fake_module.migrate_params.side_effect = lambda x: x
        fake_module.fetch.side_effect = fake_fetch

        # We're testing what happens if wf_module disappears after save, before
        # update. To mock that, delete after fetch, when saving result.
        async def fake_save(workflow_id, wf_module, *args, **kwargs):
            @database_sync_to_async
            def change_wf_module_during_fetch():
                WfModule.objects.filter(id=wf_module.id).update(
                    auto_update_data=False, next_update=None
                )

            await change_wf_module_during_fetch()

        save_result.side_effect = fake_save

        now = parser.parse("Aug 28 1999 2:34:02PM UTC")

        self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.auto_update_data, False)
        self.assertIsNone(wf_module.next_update)

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    def test_crashing_fetch(self, load_module):
        async def fake_fetch(*args, **kwargs):
            raise ValueError("boo")

        fake_module = Mock(LoadedModule)
        load_module.return_value = fake_module
        fake_module.param_schema = ParamDType.Dict({})
        fake_module.migrate_params.side_effect = lambda x: x
        fake_module.fetch.side_effect = fake_fetch

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            auto_update_data=True,
            next_update=parser.parse("Aug 28 1999 2:24PM UTC"),
            update_interval=600,
            module_id_name="x",
        )
        wf_module._module_version = (ModuleVersion(spec={"parameters": []}),)

        now = parser.parse("Aug 28 1999 2:34:02PM UTC")
        due_for_update = parser.parse("Aug 28 1999 2:44PM UTC")

        with self.assertLogs(fetch.__name__, level="ERROR") as cm:
            # We should log the actual error
            self.run_with_async_db(fetch.fetch_wf_module(workflow.id, wf_module, now))
            self.assertEqual(cm.records[0].exc_info[0], ValueError)

        wf_module.refresh_from_db()
        # [adamhooper, 2018-10-26] while fiddling with tests, I changed the
        # behavior to record the update check even when module fetch fails.
        # Previously, an exception would prevent updating last_update_check,
        # and I think that must be wrong.
        self.assertEqual(wf_module.last_update_check, now)
        self.assertEqual(wf_module.next_update, due_for_update)

    @patch("server.models.loaded_module.LoadedModule.for_module_version_sync")
    @patch("fetcher.save.save_result_if_changed")
    @patch("fetcher.fetchprep.clean_value", lambda _, params, __: params)
    def _test_fetch(
        self, fn, migrate_params_fn, wf_module, param_schema, save, load
    ) -> ProcessResult:
        """
        Stub out a `fetch` method for `wf_module`.

        Return result.
        """
        if wf_module.module_version is None:
            # White-box: we aren't testing what happens in the (valid) case
            # that a ModuleVersion has been deleted while in use. Pretend it's
            # there.
            wf_module._module_version = ModuleVersion(spec={"parameters": []})

        try:
            workflow_id = wf_module.workflow_id
        except AttributeError:  # No tab/workflow in database
            workflow_id = 1

        @dataclass(frozen=True)
        class MockLoadedModule:
            fetch: Callable
            migrate_params: Callable
            param_schema: ParamDType.Dict = ParamDType.Dict({})

        # Mock the module we load, so it calls fn() directly.
        load.return_value = MockLoadedModule(fn, migrate_params_fn)
        save.return_value = future_none

        self.run_with_async_db(
            fetch.fetch_wf_module(workflow_id, wf_module, timezone.now())
        )

        save.assert_called_once()
        self.assertEqual(save.call_args[0][0], workflow_id)
        self.assertEqual(save.call_args[0][1], wf_module)

        result = save.call_args[0][2]
        return result

    def test_fetch_get_params(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1", params={"foo": "bar"})

        async def fetch(params, **kwargs):
            self.assertEqual(params, {"foo": "bar"})

        self._test_fetch(
            fetch,
            DefaultMigrateParams,
            wf_module,
            ParamDType.Dict({"foo": ParamDType.String()}),
        )

    def test_fetch_secrets(self):
        owner = User.objects.create(username="o", email="o@example.org")
        workflow = Workflow.objects.create(owner=owner)
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(
            order=0, slug="step-1", secrets={"X": {"name": "name", "secret": "secret"}}
        )

        async def fetch(params, *, secrets, **kwargs):
            self.assertEqual(secrets, {"X": {"name": "name", "secret": "secret"}})

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_happy_path(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta.id
        )
        cache_render_result(workflow, wfm1, delta.id, ProcessResult(table))
        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        async def fetch(params, *, get_input_dataframe, **kwargs):
            assert_frame_equal(await get_input_dataframe(), table)

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_two_tabs(self):
        table = pd.DataFrame({"A": [1]})
        wrong_table = pd.DataFrame({"B": [1]})

        workflow = Workflow.create_and_init()
        delta_id = workflow.last_delta_id
        tab = workflow.tabs.first()
        wfm1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta_id
        )
        cache_render_result(workflow, wfm1, delta_id, ProcessResult(table))
        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        tab2 = workflow.tabs.create(position=1)
        wfm3 = tab2.wf_modules.create(
            order=0, slug="step-3", last_relevant_delta_id=delta_id
        )
        cache_render_result(workflow, wfm3, delta_id, ProcessResult(wrong_table))

        async def fetch(params, *, get_input_dataframe, **kwargs):
            assert_frame_equal(await get_input_dataframe(), table)

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_empty_cache(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        tab.wf_modules.create(order=0, slug="step-1", last_relevant_delta_id=delta.id)
        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_stale_cache(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta1 = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta1.id
        )
        cache_render_result(workflow, wfm1, delta1.id, ProcessResult(table))

        # Now make wfm1's output stale
        delta2 = InitWorkflowCommand.create(workflow)
        wfm1.last_relevant_delta_id = delta2.id
        wfm1.save(update_fields=["last_relevant_delta_id"])

        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_race_delete_prior_wf_module(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta.id
        )
        cache_render_result(workflow, wfm1, delta.id, ProcessResult(table))
        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because it's far too slow).
        wfm1.delete()

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_input_dataframe_race_delete_workflow(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        delta = InitWorkflowCommand.create(workflow)
        wfm1 = tab.wf_modules.create(
            order=0, slug="step-1", last_relevant_delta_id=delta.id
        )
        cache_render_result(workflow, wfm1, delta.id, ProcessResult(table))
        wfm2 = tab.wf_modules.create(order=1, slug="step-2")

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because it's far too slow).
        workflow.delete()

        async def fetch(params, *, get_input_dataframe, **kwargs):
            self.assertIsNone(await get_input_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wfm2, ParamDType.Dict({}))

    def test_fetch_get_stored_dataframe_happy_path(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")
        wf_module.stored_data_version = self._store_fetched_table(
            wf_module, table
        ).stored_at
        wf_module.save()

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            assert_frame_equal(await get_stored_dataframe(), table)

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))

    def test_fetch_get_stored_dataframe_unhandled_parquet_is_none(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")
        stored_object = self._store_fetched_table(wf_module, pd.DataFrame())
        wf_module.stored_data_version = stored_object.stored_at
        wf_module.save()
        # Overwrite with invalid Parquet data
        minio.fput_file(
            stored_object.bucket,
            stored_object.key,
            (
                Path(__file__).parent.parent.parent
                / "cjwstate"
                / "tests"
                / "test_data"
                / "fastparquet-issue-375.par"
            ),
        )

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))

    def test_fetch_get_stored_dataframe_missing_file_is_none(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")
        stored_object = self._store_fetched_table(wf_module, pd.DataFrame())
        wf_module.stored_data_version = stored_object.stored_at
        wf_module.save()
        # Delete file -- making DB and S3 inconsistent
        minio.remove(stored_object.bucket, stored_object.key)

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))

    def test_fetch_get_stored_dataframe_no_stored_data_frame(self):
        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))

    def test_fetch_get_stored_dataframe_race_delete_wf_module(self):
        table = pd.DataFrame({"A": [1]})

        workflow = Workflow.objects.create()
        tab = workflow.tabs.create(position=0)
        wf_module = tab.wf_modules.create(order=0, slug="step-1")
        wf_module.stored_data_version = self._store_fetched_table(
            wf_module, table
        ).stored_at
        wf_module.save()

        # Delete from the database. They're still in memory. This deletion can
        # happen on production: we aren't locking the workflow during fetch
        # (because fetch is far too slow).
        wf_module.delete()
        wf_module.id = 3  # simulate race: id is non-empty

        async def fetch(params, *, get_stored_dataframe, **kwargs):
            self.assertIsNone(await get_stored_dataframe())

        self._test_fetch(fetch, DefaultMigrateParams, wf_module, ParamDType.Dict({}))
