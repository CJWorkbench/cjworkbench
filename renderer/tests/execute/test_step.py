import contextlib
import datetime
import logging
import textwrap
from unittest.mock import patch

import pyarrow as pa
from cjwmodule.arrow.testing import make_column, make_table
from django.contrib.auth.models import User

from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.types import I18nMessage, RenderError
from cjwkernel.tests.util import parquet_file
from cjwstate import s3, rabbitmq, rendercache
from cjwstate.rendercache.testing import write_to_rendercache
from cjwstate.storedobjects import create_stored_object
from cjwstate.models.workflow import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from cjworkbench.models.userprofile import UserProfile
from renderer import notifications
from renderer.execute.step import execute_step


def create_test_user(
    username="username", email="user@example.org", password="password"
):
    user = User.objects.create(username=username, email=email, password=password)
    UserProfile.objects.create(user=user)
    return user


async def noop(*args, **kwargs):
    return


class StepTests(DbTestCaseWithModuleRegistry):
    def setUp(self):
        super().setUp()
        self.ctx = contextlib.ExitStack()
        self.chroot_context = self.ctx.enter_context(EDITABLE_CHROOT.acquire_context())
        basedir = self.ctx.enter_context(
            self.chroot_context.tempdir_context(prefix="test_step-")
        )
        self.empty_table_path = self.ctx.enter_context(
            self.chroot_context.tempfile_context(prefix="empty-table-", dir=basedir)
        )
        with pa.ipc.RecordBatchFileWriter(self.empty_table_path, pa.schema([])):
            pass
        self.output_path = self.ctx.enter_context(
            self.chroot_context.tempfile_context(prefix="output-", dir=basedir)
        )

    def tearDown(self):
        self.ctx.close()
        super().tearDown()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="deleted_module",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        result = self.run_with_async_db(
            execute_step(
                chroot_context=self.chroot_context,
                workflow=workflow,
                step=step,
                module_zipfile=None,
                params={},
                tab_name=tab.name,
                input_path=self.empty_table_path,
                input_table_columns=[],
                tab_results={},
                output_path=self.output_path,
            )
        )
        self.assertEqual(result.columns, [])
        self.assertEqual(self.output_path.read_bytes(), b"")

        step.refresh_from_db()
        self.assertEqual(
            step.cached_render_result.errors,
            [RenderError(I18nMessage("py.renderer.execute.step.noModule", {}, None))],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_delta(self, email_delta):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,  # stale
            make_table(make_column("A", [1])),
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )
        email_delta.assert_called()
        delta = email_delta.call_args[0][0]

        self.assertEqual(delta.user, workflow.owner)
        self.assertEqual(delta.workflow, workflow)
        self.assertEqual(delta.step, step)

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_do_not_email_delta_for_anonymous_user(self, email_delta):
        workflow = Workflow.create_and_init(
            owner_id=None, anonymous_owner_session_key="sess"
        )
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,  # stale
            make_table(make_column("A", [1])),
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )
        email_delta.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(rendercache, "downloaded_parquet_file")
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_ignore_corrupt_cache_error(self, email_delta, read_cache):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        # We need to actually populate the cache to set up the test. The code
        # under test will only try to open the render result if the database
        # says there's something there.
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,  # stale
            make_table(make_column("A", [1])),
        )
        read_cache.side_effect = rendercache.CorruptCacheError

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            # returns different data -- but CorruptCacheError means we won't care.
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )

        with self.assertLogs(level=logging.ERROR):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

        email_delta.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_when_errors_change(self, email_delta):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        # We need to actually populate the cache to set up the test. The code
        # under test will only try to open the render result if the database
        # says there's something there.
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,  # stale
            table=make_table(),
            errors=[
                RenderError(I18nMessage("py.renderer.execute.step.noModule", {}, None))
            ],
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            # returns different error
            python_code='import pandas as pd\ndef render(table, params): return [{"id": "err"}]',
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

        email_delta.assert_called()  # there's new data

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_no_delta_when_errors_stay_the_same(self, email_delta):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id - 1,
            notifications=True,
        )
        # We need to actually populate the cache to set up the test. The code
        # under test will only try to open the render result if the database
        # says there's something there.
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,  # stale
            table=make_table(),
            errors=[
                RenderError(I18nMessage("py.renderer.execute.step.noModule", {}, None))
            ],
        )

        self.run_with_async_db(
            execute_step(
                chroot_context=self.chroot_context,
                workflow=workflow,
                step=step,
                module_zipfile=None,  # will cause noModule error
                params={},
                tab_name=tab.name,
                input_path=self.empty_table_path,
                input_table_columns=[],
                tab_results={},
                output_path=self.output_path,
            )
        )

        email_delta.assert_not_called()  # error is the same error

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(rendercache, "downloaded_parquet_file")
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_when_stale_crr_is_unreachable(self, email_delta, read_cache):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        # "unreachable" previous step
        write_to_rendercache(workflow, step, workflow.last_delta_id - 1, make_table())

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            # returns different data
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

        read_cache.assert_not_called()  # it would give CorruptCacheError
        email_delta.assert_called()  # there's new data

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_when_fresh_crr_is_unreachable(self, email_delta):
        user = create_test_user()
        workflow = Workflow.create_and_init(owner_id=user.id)
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            notifications=True,
        )
        write_to_rendercache(
            workflow,
            step,
            workflow.last_delta_id - 1,
            make_table(make_column("A", [1])),
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            # returns empty result -- meaning, "unreachable"
            python_code="import pandas as pd\ndef render(table, params): return pd.DataFrame({})",
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

        email_delta.assert_called()  # there's new data -- or, well, non-data

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_happy_path(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            fetch_errors=[
                RenderError(I18nMessage("foo", {}, "module")),
                RenderError(I18nMessage("bar", {"x": "y"}, "cjwmodule")),
            ],
        )
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, step.id, path)
        step.stored_data_version = so.stored_at
        step.save(update_fields=["stored_data_version"])

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code=textwrap.dedent(
                """
                import pyarrow as pa
                import pandas as pd
                from pandas.testing import assert_frame_equal
                from cjwkernel.types import RenderError, I18nMessage

                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result.errors == [
                        RenderError(I18nMessage("foo", {}, "module")),
                        RenderError(I18nMessage("bar", {"x": "y"}, "cjwmodule")),
                    ]
                    fetch_dataframe = pa.parquet.read_table(str(fetch_result.path))
                    assert_frame_equal(fetch_dataframe, pd.DataFrame({"A": [1]}))
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_deleted_file_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, step.id, path)
        step.stored_data_version = so.stored_at
        step.save(update_fields=["stored_data_version"])
        # Now delete the file on S3 -- but leave the DB pointing to it.
        s3.remove(s3.StoredObjectsBucket, so.key)

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_deleted_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            # step.stored_data_version is buggy: it can point at a nonexistent
            # StoredObject. Do that, for this test.
            stored_data_version=datetime.datetime.now(),
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_no_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_no_bucket_or_key_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            stored_data_version=datetime.datetime.now(),
        )
        step.stored_objects.create(
            stored_at=step.stored_data_version, key="", size=0, hash="whatever"
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_render_without_input_or_loads_data_raises_no_loaded_data(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": False},
            python_code="def render(table, params): return None",
        )

        result = self.run_with_async_db(
            execute_step(
                chroot_context=self.chroot_context,
                workflow=workflow,
                step=step,
                module_zipfile=module_zipfile,
                params={},
                tab_name=tab.name,
                input_path=self.empty_table_path,
                input_table_columns=[],
                tab_results={},
                output_path=self.output_path,
            )
        )
        self.assertEqual(result.columns, [])
        self.assertEqual(self.output_path.read_bytes(), b"")

        step.refresh_from_db()
        self.assertEqual(
            step.cached_render_result.errors,
            [
                RenderError(
                    I18nMessage("py.renderer.execute.step.NoLoadedDataError", {}, None)
                )
            ],
        )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_report_module_error(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        step = tab.steps.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        module_zipfile = create_module_zipfile(
            "x",
            spec_kwargs={"loads_data": True},
            python_code="def render(table, params):\n  undefined()",
        )

        with self.assertLogs(level=logging.INFO):
            result = self.run_with_async_db(
                execute_step(
                    chroot_context=self.chroot_context,
                    workflow=workflow,
                    step=step,
                    module_zipfile=module_zipfile,
                    params={},
                    tab_name=tab.name,
                    input_path=self.empty_table_path,
                    input_table_columns=[],
                    tab_results={},
                    output_path=self.output_path,
                )
            )
        self.assertEquals(result.columns, [])
        self.assertEqual(self.output_path.read_bytes(), b"")

        step.refresh_from_db()
        self.assertEqual(
            step.cached_render_result.errors,
            [
                RenderError(
                    I18nMessage(
                        "py.renderer.execute.step.user_visible_bug_during_render",
                        {
                            "message": "exit code 1: NameError: name 'undefined' is not defined"
                        },
                        None,
                    )
                )
            ],
        )
